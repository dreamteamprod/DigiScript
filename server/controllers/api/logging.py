from typing import Any, Dict, List

from tornado import escape, httputil

from digi_server.app_server import DigiScriptServer
from digi_server.logger import get_logger, map_client_level
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion


class ClientLoggingBase(BaseAPIController):
    def __init__(
        self,
        application: DigiScriptServer,
        request: httputil.HTTPServerRequest,
        **kwargs: Any,
    ):
        super().__init__(application, request, **kwargs)
        self.client_logger = get_logger("Client")

    def process_logs(self, entries: List[Dict]):
        # Build request-level context added to every entry's extra
        request_extra = {
            "remote_ip": self.request.remote_ip,
            "agent": self.request.headers.get("User-Agent", "Unknown"),
        }
        if self.current_user:
            request_extra["user_id"] = self.current_user.get("id")
            request_extra["username"] = self.current_user.get("username")

        for entry in entries:
            level = entry.get("level", "INFO").upper()
            message = entry.get("message", "")
            extra = {**entry.get("extra", {}), **request_extra}

            log_level = map_client_level(level)

            log_msg = f"[Client] {message}"
            if extra:
                log_msg += f" | Extra: {extra}"

            self.client_logger.log(log_level, log_msg)

        self.set_status(200)
        self.write({"status": "OK"})


@ApiRoute("logs/batch", ApiVersion.V1, ignore_logging=True)
class ClientLoggingBatchController(ClientLoggingBase):
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

        self.process_logs(batch)


@ApiRoute("logs", ApiVersion.V1, ignore_logging=True)
class ClientLoggingController(ClientLoggingBase):
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
