"""Log viewer API endpoints.

Provides two admin-only endpoints backed by the in-memory log buffers
populated by :class:`~digi_server.log_buffer.LogBufferHandler`:

* ``GET /api/v1/logs/view``   — paginated one-shot snapshot
* ``GET /api/v1/logs/stream`` — Server-Sent Events (SSE) live stream with
  backfill of existing entries
"""

import asyncio
import json
import logging

from digi_server.log_buffer import get_client_buffer, get_server_buffer
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import require_admin


# Map level name → minimum level_no for "greater-than-or-equal" filtering.
# WARN is accepted as an alias for WARNING (mirrors loglevel npm behaviour).
_LEVEL_ALIASES = {
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
    "TRACE": 5,  # Custom level registered in main.py
}

_MAX_LIMIT = 1000

# Sentinel placed on the SSE queue when the client disconnects, so the
# awaiting coroutine can exit cleanly without waiting for the next timeout.
_STREAM_CLOSED = object()


def _parse_source(raw: str) -> str:
    """Normalise the ``source`` query parameter.

    :param raw: Raw value from the query string.
    :returns: ``"client"`` or ``"server"``.
    """
    return "client" if raw.lower() == "client" else "server"


def _filter_entries(
    entries: list,
    level_name: str,
    search: str,
    username_filter: str,
    source: str,
) -> list:
    """Apply all active filters to *entries* and return the matching subset.

    :param entries: List of entry dicts to filter.
    :param level_name: Uppercase level name (e.g. ``"ERROR"``); empty means
        no level filter.
    :param search: Lowercase search string; empty means no search filter.
    :param username_filter: Lowercase username substring; only applied when
        *source* is ``"client"``; empty means no filter.
    :param source: ``"server"`` or ``"client"``.
    :returns: Filtered list of entry dicts.
    """
    if level_name:
        min_level_no = _LEVEL_ALIASES.get(level_name)
        if min_level_no is not None:
            entries = [e for e in entries if e["level_no"] >= min_level_no]

    if search:
        entries = [e for e in entries if search in e["message"].lower()]

    if username_filter and source == "client":
        entries = [
            e
            for e in entries
            if e.get("username") and username_filter in e["username"].lower()
        ]

    return entries


@ApiRoute("logs/view", ApiVersion.V1, ignore_logging=True)
class LogViewerController(BaseAPIController):
    """Return a filtered snapshot of the in-memory log buffer.

    Query parameters
    ----------------
    source : str
        ``"server"`` (default) or ``"client"``.
    level : str
        Minimum level name.  Empty string (default) means all levels.
        Accepts ``TRACE``, ``DEBUG``, ``INFO``, ``WARN``/``WARNING``,
        ``ERROR``, ``CRITICAL``.
    search : str
        Case-insensitive substring match on the ``message`` field.
    username : str
        (Client source only) case-insensitive substring match on the
        ``username`` field.
    limit : int
        Maximum number of entries to return (capped at 1000, default 500).
    offset : int
        Number of entries to skip before returning (default 0).
    """

    @require_admin
    async def get(self):
        """Handle ``GET /api/v1/logs/view``.

        :raises tornado.web.HTTPError: 401 if not authenticated,
            403 if not admin.
        """
        source = _parse_source(self.get_argument("source", "server"))
        level_name = self.get_argument("level", "").upper()
        search = self.get_argument("search", "").lower()
        username_filter = self.get_argument("username", "").lower()

        try:
            limit = min(int(self.get_argument("limit", "500")), _MAX_LIMIT)
        except ValueError:
            limit = 500

        try:
            offset = max(int(self.get_argument("offset", "0")), 0)
        except ValueError:
            offset = 0

        if source == "client":
            entries = get_client_buffer().get_entries()
        else:
            entries = get_server_buffer().get_entries()

        entries = _filter_entries(entries, level_name, search, username_filter, source)

        total = len(entries)
        page = entries[offset : offset + limit]

        self.write(
            {
                "entries": page,
                "total": total,
                "returned": len(page),
                "source": source,
            }
        )


@ApiRoute("logs/stream", ApiVersion.V1, ignore_logging=True)
class LogStreamController(BaseAPIController):
    """Stream log entries to the client using Server-Sent Events (SSE).

    On connection the handler first sends all existing (backfill) entries from
    the buffer that match the active filters, then emits new entries in
    real-time as they arrive.  A ``: keepalive`` comment is written every 20 s
    to prevent proxies and browsers from closing an idle connection.

    Query parameters
    ----------------
    Same as :class:`LogViewerController` except ``limit`` and ``offset`` which
    are not applicable to a live stream.

    SSE event format
    ----------------
    Each event is a single ``data:`` line containing a JSON-encoded entry dict,
    followed by a blank line::

        data: {"ts": "...", "level": "INFO", ...}

    """

    def on_connection_close(self):
        """Called by Tornado when the client closes the connection.

        Sets a flag and pushes the :data:`_STREAM_CLOSED` sentinel onto the
        queue so the suspended ``get()`` coroutine wakes up and exits.
        """
        self._sse_closed = True
        if hasattr(self, "_sse_queue"):
            self._sse_queue.put_nowait(_STREAM_CLOSED)

    @require_admin
    async def get(self):
        """Handle ``GET /api/v1/logs/stream``.

        :raises tornado.web.HTTPError: 401 if not authenticated,
            403 if not admin.
        """
        source = _parse_source(self.get_argument("source", "server"))
        level_name = self.get_argument("level", "").upper()
        search = self.get_argument("search", "").lower()
        username_filter = self.get_argument("username", "").lower()

        self._sse_closed = False

        self.set_header("Content-Type", "text/event-stream; charset=utf-8")
        self.set_header("Cache-Control", "no-cache")
        # Instruct nginx / other reverse proxies not to buffer this response.
        self.set_header("X-Accel-Buffering", "no")

        buffer = get_client_buffer() if source == "client" else get_server_buffer()

        # Send backfill — all existing entries that pass the current filters.
        for entry in _filter_entries(
            buffer.get_entries(), level_name, search, username_filter, source
        ):
            self.write(f"data: {json.dumps(entry)}\n\n")
        await self.flush()

        # Subscribe to future entries.
        queue: asyncio.Queue = asyncio.Queue()
        self._sse_queue = queue

        unsubscribe = buffer.subscribe(queue.put_nowait)

        try:
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=20.0)
                except asyncio.TimeoutError:
                    # Send a keepalive comment so proxies don't time out.
                    if self._sse_closed:
                        break
                    self.write(": keepalive\n\n")
                    await self.flush()
                    continue

                if entry is _STREAM_CLOSED:
                    break

                matched = _filter_entries(
                    [entry], level_name, search, username_filter, source
                )
                if matched:
                    self.write(f"data: {json.dumps(matched[0])}\n\n")
                    await self.flush()
        except Exception:  # noqa: BLE001
            pass
        finally:
            unsubscribe()
