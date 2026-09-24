"""Shared WebSocket session-lifecycle operations (issue #1419).

These release or hand on the state a client session holds: edit/cut locks
(``Session.is_editor`` / ``is_cutting``), live-show leadership
(``ShowSession.client_internal_id``) and a collaborative-editing room role. They are
used by the WebSocket controller (disconnect finalisation, provisional state that
auth did not confirm) and by the REST login/logout handlers, so each path releases
state the same way and broadcasts the same notifications.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import select
from tornado.ioloop import IOLoop
from tornado.websocket import WebSocketClosedError

from digi_server.logger import get_logger
from models.session import Session, ShowSession
from models.show import Show
from utils.web.pending_disconnects import room_close_key


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


def safe_write(client: Any, message: Dict[str, Any]) -> None:
    """Send *message* to *client*, never raising.

    A failed send to one peer (for example a socket that is closing but has not
    run ``on_close`` yet) must not abort a broadcast loop or an election.

    :param client: A WebSocket handler.
    :param message: The message dict to send.
    """
    try:
        client.write_message(message)
    except WebSocketClosedError:
        get_logger().debug("Skipped message to a closed WebSocket")
    except Exception:
        get_logger().exception("Failed to send WebSocket message")


def broadcast(app: DigiScriptServer, action: str, data: Optional[dict] = None) -> None:
    """Send a ``NOOP`` message with *action* to every connected client.

    Iterates over a copy of ``app.clients``, because a failed send can call
    ``on_close`` on the peer, which removes it from that list.

    :param app: The application.
    :param action: The ``ACTION`` value.
    :param data: The ``DATA`` value (defaults to ``{}``).
    """
    message = {"OP": "NOOP", "ACTION": action, "DATA": data or {}}
    for client in list(app.clients):
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
        # Defensive: on_close removes a handler from app.clients before its uuid
        # becomes pending, and REFRESH_CLIENT cancels the pending state before a
        # live handler takes the uuid, so no connected client should hold a
        # pending uuid today. Kept so that a future change can never elect a tab
        # that is mid-reload.
        if client_id in candidate_ids and not app.pending_disconnects.is_pending(
            client_id
        ):
            return client
    return None


def elect_live_leader(app: DigiScriptServer, departed_id: str) -> None:
    """Hand live-show leadership on from *departed_id*.

    Does nothing if there is no running show session, or if someone other than
    *departed_id* already leads it. Otherwise the leader becomes the first
    connected client of the show session's user in connection order, excluding
    tabs that are pending reconnect, and is sent ``ELECTED_LEADER``. If there is no
    such client, leadership is cleared, ``NO_LEADER`` is broadcast, and
    ``last_client_internal_id`` records *departed_id* so that it can reclaim
    leadership once it authenticates as the show session's user again. The
    database change is committed before any message is sent.

    :param app: The application.
    :param departed_id: The uuid that is losing leadership.
    """
    with app.get_db().sessionmaker() as session:
        live_session = get_live_session(app, session)
        if live_session is None or live_session.client_internal_id not in (
            None,
            departed_id,
        ):
            return
        next_ws = _pick_next_leader(app, session, live_session.user_id, departed_id)
        if next_ws is not None:
            live_session.client_internal_id = next_ws.__getattribute__("internal_id")
            live_session.last_client_internal_id = None
        else:
            live_session.client_internal_id = None
            live_session.last_client_internal_id = departed_id
        latest_line_ref = live_session.latest_line_ref
        session.commit()

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
        for ws, role in list(room.clients.items())
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
) -> tuple[bool, bool]:
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
    """Take edit/cut locks and/or live-show leadership away from a live session.

    Clears the row's edit/cut flags (and its editor role in the collaborative
    room), then broadcasts ``GET_SCRIPT_CONFIG_STATUS``. If the row leads the live
    show, leadership is handed on through :func:`elect_live_leader`.

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
