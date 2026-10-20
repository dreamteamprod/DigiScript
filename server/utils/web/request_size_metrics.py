"""Prometheus histograms of inbound HTTP body and WebSocket message sizes.

The histograms are module-level so they are registered exactly once per
process, however many application instances are created (tests create many).
They are exposed alongside the other metrics at ``/debug/metrics`` and exist so
that request size limits can be tuned from real data.
"""

from __future__ import annotations

import functools

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


def observe_http_request(handler) -> None:
    """Record the body size of a finished HTTP request, if it had a body.

    The label is the handler class name (bounded), never the raw path.

    :param handler: The finished Tornado ``RequestHandler``.
    """
    size = len(handler.request.body or b"")
    if size:
        http_request_body_bytes.labels(
            type(handler).__name__, handler.request.method
        ).observe(size)


class WSMessageSizeMetricsMixin:
    """Observes the size of every message passed to a subclass's ``on_message``.

    ``on_message`` is wrapped when the subclass is created, so the subclass's
    own method body needs no changes.
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        original = cls.__dict__.get("on_message")
        if original is None:
            return

        @functools.wraps(original)
        async def on_message(self, message):
            ws_message_bytes.observe(len(message))
            return await original(self, message)

        cls.on_message = on_message
