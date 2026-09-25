"""Shared WebSocket session-lifecycle operations (issues #1419, #1424).

**Ownership rule.** A client uuid (``Session.internal_id``) is an *identity*, not a
credential. Uuids are visible to other clients (``show/sessions``,
``show/script/config``), so presenting one via ``REFRESH_CLIENT`` proves nothing.
The edit/cut lock (``Session.is_editor`` / ``is_cutting``) and live-show
leadership (``ShowSession.client_internal_id``) recorded against a uuid may only be
*used* by a connection authenticated as the row's owner (``Session.user_id``), and
leader operations also require the show session's user. The WebSocket controller
checks this each time a privilege is used.

This module holds the operations that release or hand on that state. The
WebSocket controller uses them for disconnect finalisation and for a user taking
a client over. The REST logout handler uses them too, so every path releases state
the same way and sends the same notifications.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from tornado.ioloop import IOLoop

from digi_server.logger import get_logger
from models.session import Session, ShowSession
from models.show import Show
from utils.web.pending_disconnects import disconnect_key, room_close_key


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer

#: Attempts at deleting a departed client's row before giving up.
FINALISE_ATTEMPTS = 3
#: Delay between those attempts, in seconds.
FINALISE_RETRY_SECONDS = 1.0


def _log_failed_send(client: Any, future) -> None:
    """Done-callback for a send: log it if the message could not be sent."""
    if future.cancelled():
        return
    error = future.exception()
    if error is not None:
        get_logger().error(
            f"Failed to send WebSocket message to client "
            f"{getattr(client, 'internal_id', '?')}: {error!r}"
        )


def safe_write(client: Any, message: Dict[str, Any]) -> None:
    """Send *message* to *client*, never raising, and log a failed send.

    ``WebSocketController.write_message`` is a coroutine: a failure (for example a
    message that cannot be JSON-encoded) lands in the Future it returns, not in
    an exception here, so the Future gets a done-callback that logs it together
    with the client's uuid. A closed socket is already handled inside
    ``write_message``. The ``except`` covers handlers whose ``write_message``
    raises synchronously.

    :param client: A WebSocket handler.
    :param message: The message dict to send.
    """
    try:
        future = client.write_message(message)
    except Exception:
        get_logger().exception(
            f"Failed to send WebSocket message to client "
            f"{getattr(client, 'internal_id', '?')}"
        )
        return
    if future is not None and hasattr(future, "add_done_callback"):
        future.add_done_callback(lambda fut: _log_failed_send(client, fut))


def broadcast(app: DigiScriptServer, action: str, data: Optional[dict] = None) -> None:
    """Send a ``NOOP`` message with *action* to every connected client.

    Iterates over a copy of ``app.clients``, because a failed send can call
    ``on_close`` on the peer, which removes it from that list.

    :param app: The application.
    :param action: The ``ACTION`` value.
    :param data: The ``DATA`` value (defaults to ``{}``).
    """
    message = {"OP": "NOOP", "ACTION": action, "DATA": data or {}}
    for client in app.clients.copy():
        safe_write(client, message)


def get_live_session(app: DigiScriptServer, session) -> Optional[ShowSession]:
    """Return the current show's running ShowSession, or None.

    :param app: The application.
    :param session: Active SQLAlchemy session.
    """
    show_setting = app.digi_settings.settings.get("current_show")
    current_show = show_setting.get_value() if show_setting else None
    if not current_show:
        return None
    show = session.get(Show, current_show)
    if not show or not show.current_session_id:
        return None
    return session.get(ShowSession, show.current_session_id)


def assign_session_user(entry: Session, user_id: Optional[int]) -> bool:
    """Set the user on a Session row. Edit/cut flags never pass to a different user.

    A row whose owner differs from *user_id* (including a row with no owner, for
    example after a logout) loses its edit/cut flags.

    :param entry: The Session row.
    :param user_id: The authenticated user, or None to leave the row unchanged.
    :returns: True if edit/cut flags were cleared. The caller must then broadcast
        ``GET_SCRIPT_CONFIG_STATUS`` once the change is committed.
    """
    if user_id is None or entry.user_id == user_id:
        return False
    cleared = bool(entry.is_editor or entry.is_cutting)
    entry.is_editor = False
    entry.is_cutting = False
    entry.user_id = user_id
    return cleared


def holders(app: DigiScriptServer, internal_id: str) -> List[Any]:
    """Return every connected handler that currently uses *internal_id*.

    More than one handler can hold a uuid: a reload's new socket and the old one
    that has not closed yet, same-browser client-v3 tabs (the uuid lives in
    localStorage), or a socket that presented someone else's uuid.

    :param app: The application.
    :param internal_id: The client uuid.
    """
    return [c for c in app.clients if getattr(c, "internal_id", None) == internal_id]


def row_owner(app: DigiScriptServer, internal_id: str) -> Tuple[bool, Optional[int]]:
    """Return ``(row_exists, owner_user_id)`` for the Session row *internal_id*.

    :param app: The application.
    :param internal_id: The client uuid.
    """
    with app.get_db().sessionmaker() as session:
        entry = session.get(Session, internal_id)
        return (entry is not None, entry.user_id if entry is not None else None)


def owner_is_connected(
    app: DigiScriptServer,
    internal_id: str,
    owner_id: Optional[int],
    exclude: Any = None,
) -> bool:
    """Return True if a connected handler for *internal_id* is authenticated as its owner.

    :param app: The application.
    :param internal_id: The client uuid.
    :param owner_id: The row's owner, or None (then the answer is always False).
    :param exclude: A handler to ignore (typically the caller).
    """
    if owner_id is None:
        return False
    return any(
        client is not exclude and getattr(client, "current_user_id", None) == owner_id
        for client in holders(app, internal_id)
    )


def _pick_next_leader(app: DigiScriptServer, session, user_id, departed_id: str):
    """Choose the connected client to hand leadership to, or None.

    :param app: The application.
    :param session: Active SQLAlchemy session.
    :param user_id: The show session's user. Only their clients are eligible.
    :param departed_id: The uuid that is losing leadership (never chosen).
    :returns: The first eligible handler in connection order, or None.
    """
    if user_id is None:
        return None
    candidate_ids = set(
        session.scalars(
            select(Session.internal_id).where(
                Session.user_id == user_id, Session.internal_id != departed_id
            )
        ).all()
    )
    for client in app.clients:
        client_id = getattr(client, "internal_id", None)
        # Only a handler authenticated as the show's user can lead (ownership
        # rule), so an unauthenticated socket holding a candidate uuid is skipped.
        if getattr(client, "current_user_id", None) != user_id:
            continue
        # Defensive: on_close removes a handler from app.clients before its uuid
        # becomes pending, so no connected client should hold a pending uuid with
        # its owner's authentication today. Kept so that a future change can never
        # elect a tab that is mid-reload.
        if client_id in candidate_ids and not app.pending_disconnects.is_pending(
            client_id
        ):
            return client
    return None


def elect_live_leader(app: DigiScriptServer, departed_id: str) -> None:
    """Hand live-show leadership on from *departed_id*.

    Does nothing if there is no running show session, or if someone other than
    *departed_id* already leads it. Otherwise the leader becomes the first
    connected client authenticated as the show session's user, in connection
    order, excluding tabs that are pending reconnect, and is sent
    ``ELECTED_LEADER``. If there is no such client, leadership is cleared,
    ``NO_LEADER`` is broadcast, and ``last_client_internal_id`` records
    *departed_id* so that it can reclaim leadership once it authenticates as the
    show session's user again. The database change is committed before any
    message is sent. If that commit fails, followers are still sent
    ``NO_LEADER`` so they fall back to manual scrolling rather than waiting on a
    leader that is gone.

    :param app: The application.
    :param departed_id: The uuid that is losing leadership.
    """
    next_ws = None
    latest_line_ref = None
    try:
        with app.get_db().sessionmaker() as session:
            live_session = get_live_session(app, session)
            if live_session is None or live_session.client_internal_id not in (
                None,
                departed_id,
            ):
                return
            next_ws = _pick_next_leader(app, session, live_session.user_id, departed_id)
            if next_ws is not None:
                live_session.client_internal_id = next_ws.__getattribute__(
                    "internal_id"
                )
                live_session.last_client_internal_id = None
            else:
                live_session.client_internal_id = None
                live_session.last_client_internal_id = departed_id
            latest_line_ref = live_session.latest_line_ref
            session.commit()
    except Exception:
        get_logger().exception(
            f"Leader election after {departed_id} failed to commit; telling "
            f"followers there is no leader"
        )
        next_ws = None

    if next_ws is not None:
        safe_write(
            next_ws,
            {
                "OP": "NOOP",
                "ACTION": "ELECTED_LEADER",
                "DATA": {"latest_line_ref": latest_line_ref},
            },
        )
    else:
        broadcast(app, "NO_LEADER")
    broadcast(app, "GET_SHOW_SESSION_DATA")


def schedule_room_close(app: DigiScriptServer, room) -> None:
    """Close *room* after the grace window unless an editor has (re)joined it.

    Scheduling again for the same room replaces the earlier timer, so a second
    reload inside the window cannot close the room early.

    :param app: The application.
    :param room: The collaborative-editing room whose last editor left.
    """

    def _fire():
        return close_room_if_editorless(app, room)

    app.pending_disconnects.schedule(room_close_key(room.revision_id), _fire)


async def close_room_if_editorless(app: DigiScriptServer, room) -> None:
    """Checkpoint (if dirty) and close *room* if it is still active with no editor.

    :param app: The application.
    :param room: The room that lost its last editor.
    """
    room_manager = getattr(app, "room_manager", None)
    if (
        room_manager is None
        or room_manager.get_active_room() is not room
        or room.has_editors
    ):
        return
    try:
        if room._dirty:
            await room_manager._checkpoint_room(room)
            await app.ws_send_to_all("NOOP", "GET_SCRIPT_REVISIONS", {})
    except Exception:
        get_logger().exception("Error checkpointing room after last editor left")
    finally:
        if room_manager.get_active_room() is room and not room.has_editors:
            try:
                await room_manager.close_active_room()
            except Exception:
                get_logger().exception(
                    "Error closing active room after last editor left — "
                    "room may be left in a stale state"
                )


def _downgrade_room_editor(app: DigiScriptServer, internal_id: str) -> None:
    """Make every room member holding *internal_id* a viewer.

    :param app: The application.
    :param internal_id: The uuid that lost its edit flag.
    """
    room_manager = getattr(app, "room_manager", None)
    room = room_manager.get_active_room() if room_manager else None
    if room is None:
        return
    members = [
        ws
        for ws, role in room.clients.items()
        if role == "editor" and getattr(ws, "internal_id", None) == internal_id
    ]
    if not members:
        return
    for ws in members:
        room.add_client(ws, "viewer")

    async def _broadcast_members():
        try:
            with app.get_db().sessionmaker() as session:
                await room.broadcast_members(session)
        except Exception:
            get_logger().exception("Error broadcasting room members")

    IOLoop.current().add_callback(_broadcast_members)
    if not room.has_editors:
        schedule_room_close(app, room)


def _clear_privileges(
    app: DigiScriptServer, internal_id: str, flags: bool, leadership: bool
) -> Tuple[bool, bool]:
    """Clear the row's edit/cut flags and report whether it leads the live show.

    :returns: ``(flags_cleared, was_leader)``.
    """
    flags_cleared = False
    was_leader = False
    with app.get_db().sessionmaker() as session:
        entry = session.get(Session, internal_id)
        if flags and entry is not None and (entry.is_editor or entry.is_cutting):
            entry.is_editor = False
            entry.is_cutting = False
            flags_cleared = True
        if leadership:
            live_session = get_live_session(app, session)
            was_leader = (
                live_session is not None
                and live_session.client_internal_id == internal_id
            )
        session.commit()
    return flags_cleared, was_leader


def release_session_privileges(
    app: DigiScriptServer,
    internal_id: str,
    reason: str,
    *,
    flags: bool = True,
    leadership: bool = True,
) -> None:
    """Take edit/cut locks and/or live-show leadership away from a client uuid.

    Clears the row's edit/cut flags (and its editor role in the collaborative
    room), then broadcasts ``GET_SCRIPT_CONFIG_STATUS``. If the row leads the live
    show, leadership is handed on through :func:`elect_live_leader`. Callers must
    only call this when the row's owner has gone (or is the one asking), never
    because some other connection presented the uuid.

    :param app: The application.
    :param internal_id: The session uuid.
    :param reason: Why, for the log.
    :param flags: Whether to release edit/cut flags.
    :param leadership: Whether to release live-show leadership.
    """
    flags_cleared, was_leader = _clear_privileges(app, internal_id, flags, leadership)
    released = [
        name
        for name, done in (
            ("edit/cut lock", flags_cleared),
            ("live-show leadership", was_leader),
        )
        if done
    ]
    if released:
        get_logger().info(
            f"Released {' and '.join(released)} of client {internal_id}: {reason}"
        )
    if flags_cleared:
        _downgrade_room_editor(app, internal_id)
        broadcast(app, "GET_SCRIPT_CONFIG_STATUS")
    if was_leader:
        elect_live_leader(app, internal_id)


# ----------------------------------------------------------------------
# The grace deadline for a departed client
# ----------------------------------------------------------------------


def schedule_disconnect_deadline(app: DigiScriptServer, internal_id: str) -> bool:
    """Start the grace deadline for *internal_id*, unless one is already running.

    The *original* deadline is kept: a socket that presents the uuid and then
    closes again (once, or on a loop) never pushes it back. Only an
    ``AUTHENTICATE`` as the row's owner cancels it.

    :param app: The application.
    :param internal_id: The departed client's uuid.
    :returns: True if a new deadline was started.
    """
    registry = app.pending_disconnects
    if registry.is_pending(internal_id):
        return False
    registry.schedule(
        disconnect_key(internal_id), lambda: finalise_disconnect(app, internal_id)
    )
    return True


def _delete_session_row(
    app: DigiScriptServer, internal_id: str
) -> Optional[Tuple[bool, bool]]:
    """Delete the Session row *internal_id*.

    :returns: ``(had_lock, was_leader)``, or None if there was no row.
    """
    with app.get_db().sessionmaker() as session:
        entry = session.get(Session, internal_id)
        if entry is None:
            return None
        had_lock = bool(entry.is_editor or entry.is_cutting)
        was_leader = entry.live_session is not None
        session.delete(entry)
        session.commit()
    return had_lock, was_leader


def _adopt_row_for_sole_user(app: DigiScriptServer, internal_id: str) -> None:
    """Give the row to the connected user holding it, if there is exactly one.

    Called at the deadline when the owner never came back but other connections
    still hold the uuid (for example, a browser that switched to a different
    user). If every holder is authenticated as the same user, that user becomes
    the owner. The owner's privileges have already been released by then.
    """
    users = {getattr(c, "current_user_id", None) for c in holders(app, internal_id)}
    if len(users) != 1 or None in users:
        return
    (user_id,) = users
    with app.get_db().sessionmaker() as session:
        entry = session.get(Session, internal_id)
        if entry is not None and assign_session_user(entry, user_id):
            broadcast(app, "GET_SCRIPT_CONFIG_STATUS")
        session.commit()


def finalise_disconnect(app: DigiScriptServer, internal_id: str, attempt: int = 1):
    """Grace deadline for a departed client *internal_id*.

    * If a connection authenticated as the row's owner holds the uuid again, the
      owner is back and nothing happens.
    * If other connections hold the uuid but none is authenticated as its owner,
      the owner's edit/cut lock and leadership are released. The row is kept,
      because those sockets still use it; deleting it would only have the next
      ping recreate it.
    * Otherwise the row is deleted. After the commit succeeds, a released lock is
      announced and leadership is handed on. If the delete fails, it is retried
      (:data:`FINALISE_ATTEMPTS`) and then released without deleting.

    :param app: The application.
    :param internal_id: The departed client's uuid.
    :param attempt: 1-based attempt number.
    """
    try:
        exists, owner_id = row_owner(app, internal_id)
    except Exception:
        _finalise_failed(app, internal_id, attempt)
        return
    if not exists or owner_is_connected(app, internal_id, owner_id):
        return

    if holders(app, internal_id):
        release_session_privileges(
            app,
            internal_id,
            "grace window expired and its owner did not authenticate again",
        )
        _adopt_row_for_sole_user(app, internal_id)
        return

    try:
        result = _delete_session_row(app, internal_id)
    except Exception:
        _finalise_failed(app, internal_id, attempt)
        return
    if result is None:
        return
    had_lock, was_leader = result
    if had_lock:
        broadcast(app, "GET_SCRIPT_CONFIG_STATUS")
    if was_leader:
        elect_live_leader(app, internal_id)


def _held_state(app: DigiScriptServer, internal_id: str) -> str:
    """Describe what *internal_id* still holds, for the give-up log line."""
    try:
        with app.get_db().sessionmaker() as session:
            entry = session.get(Session, internal_id)
            live_session = get_live_session(app, session)
            leader = (
                live_session is not None
                and live_session.client_internal_id == internal_id
            )
            if entry is None:
                return f"no row, leader={leader}"
            return (
                f"edit={bool(entry.is_editor)}, cut={bool(entry.is_cutting)}, "
                f"leader={leader}"
            )
    except Exception:
        return "state unknown (database unavailable)"


def _finalise_failed(app: DigiScriptServer, internal_id: str, attempt: int) -> None:
    """Retry a failed finalisation, or give up and release what we can."""
    if attempt < FINALISE_ATTEMPTS:
        get_logger().warning(
            f"Could not finalise disconnected client {internal_id} "
            f"(attempt {attempt}/{FINALISE_ATTEMPTS}); retrying",
            exc_info=True,
        )
        app.pending_disconnects.schedule(
            disconnect_key(internal_id),
            lambda: finalise_disconnect(app, internal_id, attempt + 1),
            delay=FINALISE_RETRY_SECONDS,
        )
        return

    get_logger().error(
        f"Giving up deleting the row of disconnected client {internal_id} after "
        f"{FINALISE_ATTEMPTS} attempts; falling back to releasing its "
        f"privileges without deleting it (held: {_held_state(app, internal_id)})",
        exc_info=True,
    )
    try:
        release_session_privileges(
            app, internal_id, "row could not be deleted after its grace window"
        )
    except Exception:
        get_logger().exception(
            f"Could not release privileges of disconnected client {internal_id} "
            f"either; they remain held until the server restarts "
            f"(held: {_held_state(app, internal_id)})"
        )
