"""Request size limits and the logging that makes hitting them observable.

Tornado enforces both limits itself and drops the offending request or
connection quietly (the HTTP rejection is logged at INFO on
``tornado.general`` and the WebSocket close is not logged at all). This module
adds a clear WARNING naming the limit and the client address.

The defaults were chosen from measurements of a 450 page / 18,000 line script:
the largest REST body is one page of lines (~17 KiB), the largest legitimate
WebSocket frame is a base64 Yjs update (a whole-script insert is ~14 MiB, an
edit touching every line is under 1 MiB).
"""

from __future__ import annotations

import logging

from tornado.websocket import WebSocketProtocol13

from digi_server.logger import get_logger


MIB = 1024 * 1024

#: Default maximum HTTP request body, in MiB (``--max_body_size_mb``).
DEFAULT_MAX_BODY_SIZE_MB = 5
#: Default maximum single WebSocket message, in MiB (``--max_ws_message_size_mb``).
DEFAULT_MAX_WS_MESSAGE_SIZE_MB = 64

WS_CLOSE_MESSAGE_TOO_BIG = 1009


class _BodyTooLargeFilter(logging.Filter):
    """Rewrites Tornado's INFO "Content-Length too long" record as a WARNING."""

    def __init__(self, max_body_size: int):
        super().__init__()
        self._max_body_size = max_body_size

    def filter(self, record: logging.LogRecord) -> bool:
        if "Content-Length too long" in record.getMessage():
            client = record.args[0] if record.args else "unknown client"
            record.levelno = logging.WARNING
            record.levelname = "WARNING"
            record.msg = (
                "Rejected HTTP request from %s: body exceeds the maximum of %d "
                "bytes (--max_body_size_mb)"
            )
            record.args = (client, self._max_body_size)
        return True


def install_body_limit_logging(max_body_size: int) -> logging.Filter:
    """Log a warning when an HTTP request is rejected for its body size.

    :param max_body_size: The configured limit in bytes (used in the message).
    :returns: The installed filter (so callers/tests can remove it).
    """
    log_filter = _BodyTooLargeFilter(max_body_size)
    logging.getLogger("tornado.general").addFilter(log_filter)
    return log_filter


class LoggingWebSocketProtocol(WebSocketProtocol13):
    """WebSocket protocol that logs when it closes a socket for size (1009)."""

    def close(self, code=None, reason=None):
        if code == WS_CLOSE_MESSAGE_TOO_BIG:
            handler = self.handler
            limit = getattr(self.params, "max_message_size", None)
            get_logger().warning(
                f"Closing WebSocket from {handler.request.remote_ip}: message "
                f"exceeds the maximum of {limit} bytes (--max_ws_message_size_mb)"
            )
        super().close(code, reason)
