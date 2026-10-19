import json
import time
from typing import Any, Dict, List, Optional

from tornado import escape, httputil

from digi_server.app_server import DigiScriptServer
from digi_server.logger import get_logger, map_client_level
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import api_authenticated


#: Maximum number of entries accepted in one batch request.
MAX_BATCH_ENTRIES = 100
#: Maximum length (characters) of a single log message; longer ones are truncated.
MAX_MESSAGE_LENGTH = 4096
#: Maximum serialised size (characters) of an entry's ``extra``; larger is replaced.
MAX_EXTRA_LENGTH = 4096
#: Per-IP budget: at most this many log entries per window.
RATE_LIMIT_ENTRIES = 600
RATE_LIMIT_WINDOW_SECONDS = 60.0


class ClientLogRateLimiter:
    """Fixed-window, per-IP limiter on the number of client log entries.

    One instance lives on the application object, so no state is shared between
    application instances (or test workers).
    """

    def __init__(
        self,
        limit: int = RATE_LIMIT_ENTRIES,
        window: float = RATE_LIMIT_WINDOW_SECONDS,
    ):
        self.limit = limit
        self.window = window
        self._windows: Dict[str, tuple] = {}

    def check(self, key: str, cost: int, now: Optional[float] = None) -> float:
        """Try to consume *cost* entries for *key*.

        :param key: The client identifier (IP address).
        :param cost: Number of entries in the request.
        :param now: Current monotonic time; defaults to ``time.monotonic()``.
        :returns: 0 if allowed, otherwise the seconds until the window resets.
        """
        now = time.monotonic() if now is None else now
        # Drop expired windows so the dict stays bounded by active clients.
        expired = [
            ip for ip, (start, _) in self._windows.items() if now - start >= self.window
        ]
        for ip in expired:
            del self._windows[ip]
        start, used = self._windows.get(key, (now, 0))
        if used + cost > self.limit:
            return max(self.window - (now - start), 1.0)
        self._windows[key] = (start, used + cost)
        return 0.0


def _clean_text(value: Any, limit: int) -> str:
    """Coerce *value* to a bounded, single-line string safe to write to a log."""
    text = value if isinstance(value, str) else str(value)
    if len(text) > limit:
        text = text[:limit] + "...[truncated]"
    return text.replace("\r", "\\r").replace("\n", "\\n")


def _clean_extra(value: Any) -> Dict:
    """Return *value* if it is a small JSON-serialisable dict, else a stand-in."""
    if not isinstance(value, dict):
        return {}
    try:
        if len(json.dumps(value, default=str)) > MAX_EXTRA_LENGTH:
            return {"extra": "[omitted: too large]"}
    except (TypeError, ValueError):
        return {"extra": "[omitted: not serialisable]"}
    return {str(k): v for k, v in value.items()}


class ClientLoggingBase(BaseAPIController):
    def __init__(
        self,
        application: DigiScriptServer,
        request: httputil.HTTPServerRequest,
        **kwargs: Any,
    ):
        super().__init__(application, request, **kwargs)
        self.client_logger = get_logger("Client")

    def process_logs(self, entries: List[Any]):
        """Validate, bound and write a list of client log entries.

        Responds 429 (with ``Retry-After``) if the caller's IP exceeded its budget.

        :param entries: The raw entries from the request body.
        """
        limiter = getattr(self.application, "client_log_limiter", None)
        if limiter is None:
            limiter = ClientLogRateLimiter()
            self.application.client_log_limiter = limiter
        retry_after = limiter.check(self.request.remote_ip or "unknown", len(entries))
        if retry_after:
            self.set_status(429)
            self.set_header("Retry-After", str(int(retry_after) + 1))
            self.write({"message": "Too many log entries"})
            return

        # Build request-level context added to every entry's extra
        request_extra = {
            "remote_ip": self.request.remote_ip,
            "agent": _clean_text(
                self.request.headers.get("User-Agent", "Unknown"), 256
            ),
        }
        if self.current_user:
            request_extra["user_id"] = self.current_user.get("id")
            request_extra["username"] = self.current_user.get("username")

        for entry in entries:
            if not isinstance(entry, dict):
                continue
            level = _clean_text(entry.get("level", "INFO"), 16).upper()
            message = _clean_text(entry.get("message", ""), MAX_MESSAGE_LENGTH)
            extra = {**_clean_extra(entry.get("extra")), **request_extra}

            log_level = map_client_level(level)

            log_msg = f"[Client] {message}"
            if extra:
                log_msg += f" | Extra: {extra}"

            # Pass structured fields via extra so LogBufferHandler can read them.
            # Tornado's LogFormatter ignores unknown extra fields, so file output
            # is unaffected.
            self.client_logger.log(
                log_level,
                log_msg,
                extra={
                    "user_id": request_extra.get("user_id"),
                    "username": request_extra.get("username"),
                    "remote_ip": request_extra.get("remote_ip"),
                },
            )

        self.set_status(200)
        self.write({"status": "OK"})


@ApiRoute("logs/batch", ApiVersion.V1, ignore_logging=True)
class ClientLoggingBatchController(ClientLoggingBase):
    @api_authenticated
    async def post(self):
        client_log_enabled = await self.application.digi_settings.get(
            "client_log_enabled"
        )
        if not client_log_enabled:
            self.set_status(403)
            self.write({"message": "Client logging is disabled"})
            return

        try:
            data = escape.json_decode(self.request.body)
        except ValueError:
            self.set_status(400)
            self.write({"message": "Invalid JSON"})
            return

        if not isinstance(data, dict):
            self.set_status(400)
            self.write({"message": "Expected JSON object with 'batch' key"})
            return

        batch = data.get("batch")
        if not isinstance(batch, list):
            self.set_status(400)
            self.write({"message": "Expected 'batch' to be a list of log entries"})
            return

        if len(batch) > MAX_BATCH_ENTRIES:
            self.set_status(413)
            self.write(
                {"message": f"Batch exceeds the {MAX_BATCH_ENTRIES} entry limit"}
            )
            return

        self.process_logs(batch)


@ApiRoute("logs", ApiVersion.V1, ignore_logging=True)
class ClientLoggingController(ClientLoggingBase):
    @api_authenticated
    async def post(self):
        client_log_enabled = await self.application.digi_settings.get(
            "client_log_enabled"
        )
        if not client_log_enabled:
            self.set_status(403)
            self.write({"message": "Client logging is disabled"})
            return

        try:
            data = escape.json_decode(self.request.body)
        except ValueError:
            self.set_status(400)
            self.write({"message": "Invalid JSON"})
            return

        self.process_logs([data])
