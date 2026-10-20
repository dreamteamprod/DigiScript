"""Prometheus histograms of inbound HTTP body and WebSocket message sizes.

The histograms are module-level so they are registered exactly once per
process, however many application instances are created (tests create many).
They are exposed alongside the other metrics at ``/debug/metrics`` and exist so
that request size limits can be tuned from real data.
"""

from __future__ import annotations

import functools
import inspect

from prometheus_client import Histogram


# Powers of 4 from 1 KiB to 256 MiB.
SIZE_BUCKETS = tuple(1024 * 4**i for i in range(10))

http_request_body_bytes = Histogram(
    name="digiscript_http_request_body_bytes",
    documentation="Size of HTTP request bodies in bytes (requests with a body only)",
    buckets=SIZE_BUCKETS,
    labelnames=("handler", "method"),
)

ws_message_bytes = Histogram(
    name="digiscript_ws_message_bytes",
    documentation="Size of inbound WebSocket messages in bytes",
    buckets=SIZE_BUCKETS,
)


_KNOWN_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})


def observe_http_request(handler) -> None:
    """Record the body size of a finished HTTP request, if it had a body.

    Both labels are bounded: the handler class name (never the raw path) and
    the HTTP method, with anything outside the standard set reported as
    ``OTHER`` so a client cannot create unlimited series.

    :param handler: The finished Tornado ``RequestHandler``.
    """
    size = len(handler.request.body or b"")
    if size:
        method = handler.request.method
        http_request_body_bytes.labels(
            type(handler).__name__, method if method in _KNOWN_METHODS else "OTHER"
        ).observe(size)


class WSMessageSizeMetricsMixin:
    """Observes the size in bytes of every message passed to ``on_message``.

    ``on_message`` is wrapped when the subclass is created, so the subclass's
    own method body needs no changes. The subclass must define an ``async``
    ``on_message`` directly in its class body; anything else fails at import
    time rather than silently recording nothing. A subclass that overrides
    ``on_message`` and calls ``super().on_message`` is observed once per
    message, not twice.
    """

    _observing_ws_size = False

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        original = cls.__dict__.get("on_message")
        if original is None or not inspect.iscoroutinefunction(original):
            raise TypeError(
                f"{cls.__name__} must define an async on_message to use "
                "WSMessageSizeMetricsMixin"
            )

        @functools.wraps(original)
        async def on_message(self, message):
            if self._observing_ws_size:
                return await original(self, message)
            size = (
                len(message.encode("utf-8"))
                if isinstance(message, str)
                else len(message)
            )
            ws_message_bytes.observe(size)
            self._observing_ws_size = True
            try:
                return await original(self, message)
            finally:
                self._observing_ws_size = False

        cls.on_message = on_message
