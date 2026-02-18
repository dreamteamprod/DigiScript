import logging

from tornado import escape

from digi_server.logger import get_logger
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion


@ApiRoute("logs", ApiVersion.V1)
class ClientLoggingController(BaseAPIController):
    async def prepare(self):
        # Override prepare to allow logs from unauthenticated clients
        # but still run the base prepare to populate current_user if available
        await super().prepare()

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

        level = data.get("level", "INFO").upper()
        message = data.get("message", "")
        extra = data.get("extra", {})

        # Add user info if available
        if self.current_user:
            extra["user_id"] = self.current_user.get("id")
            extra["username"] = self.current_user.get("username")

        extra["remote_ip"] = self.request.remote_ip
        extra["agent"] = self.request.headers.get("User-Agent", "Unknown")

        # Map string level to logging level
        log_level = getattr(logging, level, logging.INFO)

        # Get a special logger for client logs
        client_logger = get_logger("Client")

        # Log the message.
        # Tornado's logger might not handle 'extra' in the way we want directly
        # but we can format it into the message or use it if the formatter is set up.
        # For now, let's include it in the message for visibility.
        log_msg = f"[Client] {message}"
        if extra:
            log_msg += f" | Extra: {extra}"

        client_logger.log(log_level, log_msg)

        self.set_status(200)
        self.write({"status": "OK"})
