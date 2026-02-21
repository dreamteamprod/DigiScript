"""In-memory circular log buffer.

Provides a :class:`LogBufferHandler` that stores the last N log records as
structured dicts in a :class:`collections.deque`.  Two module-level singletons
are maintained — one for server-side logs and one for client-side logs — so
the log viewer endpoint can read from either without constructing new objects.

Design rationale
----------------
* Tornado is single-threaded; ``emit()`` is always called from the IOLoop
  thread, so no mutex is required.
* ``deque(maxlen=N)`` provides O(1) append with automatic eviction of the
  oldest entry when the buffer is full.
* ``list(deque)`` is GIL-atomic in CPython, making snapshot reads safe even
  if a background thread were to emit a record concurrently.
"""

import logging
from collections import deque
from datetime import datetime, timezone
from typing import Optional


class LogBufferHandler(logging.Handler):
    """A logging handler that stores records in an in-memory circular buffer.

    :param maxlen: Maximum number of entries to keep.  When full, the oldest
        entry is evicted automatically.
    """

    def __init__(self, maxlen: int = 2000):
        super().__init__()
        self._buffer: deque = deque(maxlen=maxlen)
        self._subscribers: set = set()

    def emit(self, record: logging.LogRecord) -> None:
        """Build a structured dict from *record* and append it to the buffer.

        Extra attributes ``user_id``, ``username``, and ``remote_ip`` are read
        via :func:`getattr` so they are optional; missing attributes become
        ``None`` in the entry dict.

        :param record: The log record to store.
        """
        try:
            ts = datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(
                timespec="milliseconds"
            )
            entry = {
                "ts": ts,
                "level": record.levelname,
                "level_no": record.levelno,
                "logger": record.name,
                "message": record.getMessage(),
                "filename": record.filename,
                "lineno": record.lineno,
                "user_id": getattr(record, "user_id", None),
                "username": getattr(record, "username", None),
                "remote_ip": getattr(record, "remote_ip", None),
            }
            self._buffer.append(entry)
            for cb in list(self._subscribers):
                try:
                    cb(entry)
                except Exception:  # noqa: BLE001
                    pass
        except Exception:  # noqa: BLE001
            self.handleError(record)

    def get_entries(self) -> list:
        """Return a snapshot of all buffered entries as a plain list.

        The returned list is independent of the internal deque; subsequent
        ``emit()`` calls do not affect it.

        :returns: List of entry dicts ordered oldest-first.
        """
        return list(self._buffer)

    def subscribe(self, callback) -> "callable":
        """Register *callback* to be called with each new entry dict.

        The callback is invoked synchronously inside :meth:`emit`, on the
        Tornado IOLoop thread, immediately after the entry is appended to the
        buffer.  Callbacks must be non-blocking.

        :param callback: A callable that accepts one positional argument (the
            entry dict).
        :returns: An unsubscribe callable.  Call it to deregister *callback*.
        """
        self._subscribers.add(callback)

        def _unsubscribe():
            self._subscribers.discard(callback)

        return _unsubscribe

    def resize(self, maxlen: int) -> None:
        """Resize the buffer, preserving as many recent entries as possible.

        When shrinking, the *newest* ``maxlen`` entries are kept.

        :param maxlen: New maximum number of entries.
        """
        new_buf: deque = deque(self._buffer, maxlen=maxlen)
        self._buffer = new_buf


# Module-level singletons — one per log source.
_server_buffer: Optional[LogBufferHandler] = None
_client_buffer: Optional[LogBufferHandler] = None


def get_server_buffer() -> LogBufferHandler:
    """Return (creating if necessary) the server-side log buffer singleton.

    :returns: The server :class:`LogBufferHandler` instance.
    """
    global _server_buffer  # noqa: PLW0603
    if _server_buffer is None:
        _server_buffer = LogBufferHandler()
    return _server_buffer


def get_client_buffer() -> LogBufferHandler:
    """Return (creating if necessary) the client-side log buffer singleton.

    :returns: The client :class:`LogBufferHandler` instance.
    """
    global _client_buffer  # noqa: PLW0603
    if _client_buffer is None:
        _client_buffer = LogBufferHandler()
    return _client_buffer
