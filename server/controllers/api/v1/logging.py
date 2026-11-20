import json
import time
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

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


class _Window(NamedTuple):
    """A client's current rate-limit window."""

    start: float
    used: int


class ClientLogRateLimiter:
    """Fixed-window, per-IP limiter on the number of client log entries.

    One instance lives on the application object, so no state is shared between
    application instances (or test workers). Clients are keyed by raw IP address,
    so users sharing an IP (NAT, proxy) share one budget.
    """

    def __init__(
        self,
        limit: int = RATE_LIMIT_ENTRIES,
        window: float = RATE_LIMIT_WINDOW_SECONDS,
    ):
        """
        :param limit: Entries allowed per window; must be positive.
        :param window: Window length in seconds; must be positive.
        :raises ValueError: If *limit* or *window* is not positive.
        """
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self.limit = limit
        self.window = window
        self._windows: Dict[str, _Window] = {}

    def check(
        self, key: str, cost: int, now: Optional[float] = None
    ) -> Optional[float]:
        """Try to consume *cost* entries for *key*.

        :param key: The client identifier (IP address).
        :param cost: Number of entries in the request.
        :param now: Current monotonic time; defaults to ``time.monotonic()``.
        :returns: None if allowed, otherwise the seconds (at least 1) until the
            window resets.
        """
        now = time.monotonic() if now is None else now
        # Runs on every call (not periodically): this bounds memory and is also what
        # resets a key's window once it has expired.
        expired = [
            ip for ip, win in self._windows.items() if now - win.start >= self.window
        ]
        for ip in expired:
            del self._windows[ip]
        win = self._windows.get(key, _Window(now, 0))
        if win.used + cost > self.limit:
            return max(self.window - (now - win.start), 1.0)
        self._windows[key] = _Window(win.start, win.used + cost)
        return None


def _clean_text(value: Any, limit: int) -> str:
    """Coerce *value* to a bounded, single-line string safe to write to a log."""
    text = value if isinstance(value, str) else str(value)
    if len(text) > limit:
        text = text[:limit] + "...[truncated]"
    return text.replace("\r", "\\r").replace("\n", "\\n")


def _clean_extra(value: Any) -> Tuple[Dict, Optional[str]]:
    """Sanitise an entry's client-supplied ``extra``.

    :param value: The raw ``extra`` value.
    :returns: A ``(extra, omitted_reason)`` pair. A small JSON-serialisable dict is
        returned as-is with no reason. Non-dict input is dropped silently
        (``{}``, no reason). An oversized or non-serialisable dict is replaced by
        ``{}`` with a reason, which the caller records under a server-controlled
        key so a client cannot forge it.
    """
    if not isinstance(value, dict):
        return {}, None
    try:
        if len(json.dumps(value, default=str)) > MAX_EXTRA_LENGTH:
            return {}, "too large"
    except (TypeError, ValueError, RecursionError):
        return {}, "not serialisable"
    return {str(k): v for k, v in value.items()}, None


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
        if retry_after is not None:
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

        dropped = 0
        for entry in entries:
            if not isinstance(entry, dict):
                dropped += 1
                continue
            level = _clean_text(entry.get("level", "INFO"), 16).upper()
            message = _clean_text(entry.get("message", ""), MAX_MESSAGE_LENGTH)
            client_extra, omitted = _clean_extra(entry.get("extra"))
            # Server-set keys come last so a client cannot forge them.
            extra = {**client_extra, **request_extra}
            if omitted:
                extra["extra_omitted"] = omitted

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

        if dropped:
            get_logger().warning(
                f"Dropped {dropped} malformed client log entries from "
                f"{request_extra['remote_ip']}"
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
        except (ValueError, RecursionError):
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
        except (ValueError, RecursionError):
            self.set_status(400)
            self.write({"message": "Invalid JSON"})
            return

        if not isinstance(data, dict):
            self.set_status(400)
            self.write({"message": "Expected a JSON object log entry"})
            return

        self.process_logs([data])
