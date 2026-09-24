"""Reconnect grace window: deferred, cancellable timers for WebSocket session state.

A browser reload closes the page's WebSocket and opens a new one, which then sends
``REFRESH_CLIENT`` to resume the old client uuid. The old socket's close and the new
socket's ``REFRESH_CLIENT`` race each other. If the close finalised straight away
(deleting the ``Session`` row, releasing edit/cut locks, re-electing the live-show
leader, closing the collaborative-editing room), the reload would lose that state.

Instead, everything that a reconnect may reclaim is released by a timer held in this
registry, after :attr:`PendingDisconnects.grace_seconds`. See issue #1419. The
registry is the only owner of those timers and of the window length. Each timer has
a key, and scheduling an existing key replaces the old timer. The key helpers below
define the timer kinds:

* :func:`disconnect_key`: finalise a closed client's Session row and leadership.
  ``REFRESH_CLIENT`` for the uuid cancels it.
* :func:`provisional_key`: revoke flags and leadership that a ``REFRESH_CLIENT``
  adopted but no ``AUTHENTICATE`` for the row's owner has confirmed yet.
* :func:`room_close_key`: close the collaborative-editing room if its last editor
  has not come back.
"""

from __future__ import annotations

from typing import Awaitable, Callable, Dict, Hashable, Optional, Tuple

from tornado.ioloop import IOLoop


#: Default reconnect grace window, in seconds: how long a disconnected client's
#: state (edit/cut locks, live-show leadership, the collaborative-editing room) is
#: held for a reconnect before it is released. Tests change it through
#: ``DigiScriptServer.pending_disconnects.grace_seconds``.
WS_RECONNECT_GRACE_SECONDS = 5.0

GraceCallback = Callable[[], Optional[Awaitable[None]]]


def disconnect_key(internal_id: str) -> Tuple[str, str]:
    """Key of the timer that finalises the disconnected client *internal_id*."""
    return ("disconnect", internal_id)


def provisional_key(internal_id: str) -> Tuple[str, str]:
    """Key of the timer that revokes unconfirmed state adopted by *internal_id*."""
    return ("provisional", internal_id)


def room_close_key(revision_id: int) -> Tuple[str, int]:
    """Key of the timer that closes the room for *revision_id* if it has no editor."""
    return ("room-close", revision_id)


class PendingDisconnects:
    """Registry of grace-window timers, one per key. There is one per application."""

    def __init__(self, grace_seconds: float = WS_RECONNECT_GRACE_SECONDS) -> None:
        """
        :param grace_seconds: Default delay for :meth:`schedule`, in seconds.
        """
        self.grace_seconds = grace_seconds
        self._timers: Dict[Hashable, Tuple[object, GraceCallback]] = {}

    def schedule(
        self, key: Hashable, callback: GraceCallback, delay: Optional[float] = None
    ) -> None:
        """Run *callback* after *delay* seconds (default: the grace window).

        Replaces any timer already scheduled under *key*, so only the latest
        schedule for a key ever fires.

        :param key: Timer key, from one of the module's key helpers.
        :param callback: Called with no arguments when the timer fires. It may
            return an awaitable, which the IOLoop runs and logs errors from.
        :param delay: Seconds to wait. Negative values are clamped to 0, and None
            means :attr:`grace_seconds`.
        """
        self.cancel(key)
        seconds = self.grace_seconds if delay is None else delay
        handle = IOLoop.current().call_later(max(0.0, seconds), self._fire, key)
        self._timers[key] = (handle, callback)

    def _fire(self, key: Hashable) -> Optional[Awaitable[None]]:
        """IOLoop entry point for the timer under *key*.

        Removes the key from the registry *before* running the callback, so the
        registry stays clean if the callback raises, and the callback may schedule
        the same key again (for example to retry).

        :param key: The firing timer's key.
        :returns: Whatever the callback returns (an awaitable, or None).
        """
        entry = self._timers.pop(key, None)
        if entry is None:
            return None
        return entry[1]()

    async def fire(self, key: Hashable) -> bool:
        """Run the timer under *key* now instead of waiting for it, and await it.

        Used by tests to step through the grace window deterministically.

        :param key: Timer key.
        :returns: True if a timer was scheduled under *key* and has now run.
        """
        entry = self._timers.get(key)
        if entry is None:
            return False
        IOLoop.current().remove_timeout(entry[0])
        result = self._fire(key)
        if result is not None:
            await result
        return True

    def cancel(self, key: Hashable) -> bool:
        """Cancel the timer under *key*, if there is one.

        :param key: Timer key.
        :returns: True if a timer was cancelled.
        """
        entry = self._timers.pop(key, None)
        if entry is None:
            return False
        IOLoop.current().remove_timeout(entry[0])
        return True

    def cancel_all(self) -> None:
        """Cancel every scheduled timer (for shutdown and test teardown)."""
        # Copy: cancel() removes keys from the dict being iterated.
        for key in self._timers.copy():
            self.cancel(key)

    def is_scheduled(self, key: Hashable) -> bool:
        """Return True if a timer is scheduled under *key*.

        :param key: Timer key.
        """
        return key in self._timers

    def is_pending(self, internal_id: str) -> bool:
        """Return True if *internal_id* has disconnected and is inside its grace window.

        :param internal_id: The client uuid.
        """
        return self.is_scheduled(disconnect_key(internal_id))
