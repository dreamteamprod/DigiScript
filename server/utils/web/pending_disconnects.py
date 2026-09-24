"""Deferred finalisation of disconnected WebSocket clients.

A browser reload closes the page's WebSocket and opens a new one, which then sends
``REFRESH_CLIENT`` to resume the old client uuid. The old socket's close and the new
socket's ``REFRESH_CLIENT`` race each other. If the close finalised straight away
(deleting the ``Session`` row, releasing edit/cut locks, re-electing the live-show
leader), the reload would lose that state.

Instead, the close is registered here and finalised only after a short grace window.
``REFRESH_CLIENT`` for the same uuid cancels the pending finalisation, so the
reconnecting page resumes the real state. See issue #1419.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Dict, Optional

from tornado.ioloop import IOLoop


#: Default reconnect grace window, in seconds. This is how long a disconnected
#: client's state (edit/cut locks, live-show leadership) is held for a reconnect
#: before it is released. The server exposes it as
#: ``DigiScriptServer.ws_reconnect_grace_seconds`` so tests can shorten or lengthen it.
WS_RECONNECT_GRACE_SECONDS = 5.0


class PendingDisconnects:
    """Registry of client uuids whose disconnect finalisation is scheduled.

    One registry per application. At most one finalisation is pending per uuid.
    """

    def __init__(self) -> None:
        self._handles: Dict[str, object] = {}

    def schedule(
        self,
        internal_id: str,
        delay: float,
        callback: Callable[[], Optional[Awaitable[None]]],
    ) -> None:
        """Schedule *callback* to finalise *internal_id* after *delay* seconds.

        Replaces any finalisation already pending for the same uuid.

        :param internal_id: The client uuid being finalised.
        :param delay: Grace window in seconds (values below 0 are treated as 0).
        :param callback: Called with no arguments when the window expires. It may
            return an awaitable, which the IOLoop runs and logs errors from.
        """
        self.cancel(internal_id)
        self._handles[internal_id] = IOLoop.current().call_later(
            max(0.0, delay), self._fire, internal_id, callback
        )

    def _fire(
        self,
        internal_id: str,
        callback: Callable[[], Optional[Awaitable[None]]],
    ) -> Optional[Awaitable[None]]:
        self._handles.pop(internal_id, None)
        return callback()

    def cancel(self, internal_id: str) -> bool:
        """Cancel the pending finalisation for *internal_id*, if there is one.

        :param internal_id: The client uuid.
        :returns: True if a pending finalisation was cancelled.
        """
        handle = self._handles.pop(internal_id, None)
        if handle is None:
            return False
        IOLoop.current().remove_timeout(handle)
        return True

    def is_pending(self, internal_id: str) -> bool:
        """Return True if *internal_id* is disconnected and inside its grace window.

        :param internal_id: The client uuid.
        :returns: Whether a finalisation is pending for it.
        """
        return internal_id in self._handles
