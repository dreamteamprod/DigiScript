from __future__ import annotations

import base64
import datetime
import json
from typing import TYPE_CHECKING, Any, Awaitable, Dict, Optional, Union
from uuid import uuid4

from sqlalchemy import select
from tornado import gen
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from tornado.websocket import WebSocketClosedError, WebSocketHandler

from controllers.api.constants import (
    ERROR_COLLAB_EDITING_DISABLED,
    ERROR_COLLAB_EDITING_ENABLED,
    ERROR_CUTS_BLOCKED_BY_CUTTER,
    ERROR_CUTS_BLOCKED_BY_DRAFT,
    ERROR_CUTS_BLOCKED_BY_EDITOR,
    ERROR_EDIT_BLOCKED_BY_CUTTER,
    ERROR_EDIT_BLOCKED_BY_EDITOR,
    ERROR_EDIT_BLOCKED_BY_LIVE_SESSION,
    ERROR_INSUFFICIENT_PERMISSIONS,
)
from digi_server.logger import get_logger
from digi_server.settings import COLLAB_EDITING_SETTING
from models.script import Script
from models.session import Interval, Session, ShowSession
from models.show import Act, Show
from models.user import User
from rbac.role import Role
from utils.web.base_controller import DatabaseMixin
from utils.web.route import ApiRoute, ApiVersion


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


# Collab-room operations that are refused when collaborative editing is switched off.
_COLLAB_ONLY_OPS = frozenset(
    {
        "JOIN_SCRIPT_ROOM",
        "YJS_SYNC",
        "YJS_UPDATE",
        "YJS_AWARENESS",
        "SAVE_SCRIPT_DRAFT",
        "DISCARD_SCRIPT_DRAFT",
    }
)


@ApiRoute("ws", ApiVersion.V1)
class WebSocketController(DatabaseMixin, WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.application: DigiScriptServer = application
        self.current_user_id = None
        self.current_username: str | None = None
        self._last_ping = 0.0
        self._last_pong = 0.0
        # on_close can be invoked twice (by Tornado, and by write_message on a
        # closed socket); only the first call may act.
        self._close_handled = False

    @staticmethod
    def _assign_session_user(entry: Session, user_id: Optional[int]) -> None:
        """Set the user on a Session row, dropping privileges held by another user.

        A resumed uuid keeps its edit/cut flags only while the same user holds it.
        If a different user authenticates on it, the flags are cleared so a lock
        never passes from one user to another.

        :param entry: The Session row.
        :param user_id: The authenticated user, or None to leave it unchanged.
        """
        if user_id is None or entry.user_id == user_id:
            return
        if entry.user_id is not None:
            entry.is_editor = False
            entry.is_cutting = False
        entry.user_id = user_id

    def update_session(self, user_id=None):
        """Create or refresh the Session row for this connection's uuid.

        Edit/cut flags are never set here: they change only through
        ``REQUEST_SCRIPT_EDIT`` / ``REQUEST_SCRIPT_CUTS`` / ``STOP_SCRIPT_EDIT``,
        and are carried across a reload by ``REFRESH_CLIENT`` resuming the
        existing row.

        :param user_id: Authenticated user id, or None to leave it unchanged.
        """
        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__("internal_id"))
            if entry:
                entry.last_ping = self._last_ping
                entry.last_pong = self._last_pong
                self._assign_session_user(entry, user_id)
            else:
                session.add(
                    Session(
                        internal_id=self.__getattribute__("internal_id"),
                        remote_ip=self.request.remote_ip,
                        last_ping=self._last_ping,
                        last_pong=self._last_pong,
                        user_id=user_id,
                    )
                )
            if self.current_user_id:
                user = session.get(User, self.current_user_id)
                user.last_seen = datetime.datetime.now(tz=datetime.timezone.utc)
            session.commit()

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(f"Data streaming not supported for {self.__class__}")

    def check_origin(self, origin):
        if self.settings.get("debug", False):
            return True
        return super().check_origin(origin)

    @gen.coroutine
    def open(self, *args: str, **kwargs: str) -> Optional[Awaitable[None]]:
        self.__setattr__("internal_id", str(uuid4()))
        self.application.clients.append(self)

        self.update_session(user_id=self.current_user_id)
        get_logger().info(f"WebSocket opened from: {self.request.remote_ip}")

        yield self.write_message(
            {"OP": "SET_UUID", "DATA": self.__getattribute__("internal_id")}
        )
        yield self.write_message({"OP": "NOOP", "DATA": {}, "ACTION": "GET_SETTINGS"})

    def on_close(self) -> None:
        """Handle the socket closing.

        The close is *not* treated as final. Tornado calls this when the socket
        drops, and ``write_message`` calls it again if a write finds the socket
        closed, so it only acts once per handler. Everything that a reloading page
        can reclaim (the ``Session`` row with its edit/cut flags, live-show
        leadership, the collaborative-editing room) is released only after the
        reconnect grace window (``application.ws_reconnect_grace_seconds``) by
        :meth:`_finalise_disconnect`. ``REFRESH_CLIENT`` for the same uuid cancels
        that. See issue #1419.
        """
        if self._close_handled:
            return
        self._close_handled = True

        if self in self.application.clients:
            self.application.clients.remove(self)

        internal_id = getattr(self, "internal_id", None)
        grace = self.application.ws_reconnect_grace_seconds

        # This handler is dead, so it leaves the collaborative-editing room now.
        # Closing the room when its last editor leaves is deferred to the end of
        # the grace window, so a reloading editor that rejoins in time keeps the
        # room (and its viewers never see ROOM_CLOSED).
        room_manager = getattr(self.application, "room_manager", None)
        if room_manager:
            room = room_manager.get_room_for_client(self)
            if room:
                was_editor = room.clients.get(self) == "editor"
                room.remove_client(self)
                app = self.application

                async def _broadcast_members():
                    try:
                        with app.get_db().sessionmaker() as session:
                            await room.broadcast_members(session)
                    except Exception:
                        get_logger().exception("Error in on_close members broadcast")

                IOLoop.current().add_callback(_broadcast_members)
                if was_editor and not room.has_editors:
                    IOLoop.current().call_later(
                        max(0.0, grace), self._close_room_if_editorless, room
                    )

        user_part = (
            f"{self.current_username} ({self.request.remote_ip})"
            if self.current_username
            else self.request.remote_ip
        )

        if internal_id is None:
            get_logger().info(f"WebSocket closed from: {user_part}")
            return

        if self.application.get_ws(internal_id) is not None:
            # A newer connection has already resumed this uuid through
            # REFRESH_CLIENT, so the Session row and leadership belong to the live
            # handler. This one is stale and must not finalise them.
            get_logger().info(
                f"WebSocket closed from: {user_part} (client {internal_id} already "
                f"resumed by a newer connection; nothing to release)"
            )
            return

        self.application.pending_disconnects.schedule(
            internal_id, grace, self._finalise_disconnect
        )
        get_logger().info(
            f"WebSocket closed from: {user_part} (client {internal_id} held for "
            f"{grace:g}s reconnect grace window)"
        )

    def _finalise_disconnect(self) -> None:
        """Release a disconnected client's state once its grace window has expired.

        Deletes the ``Session`` row. If the row held an edit or cut lock, tells
        every client to re-fetch the script config status. If the row was the
        live-show leader, runs leader election. Does nothing if a live connection
        holds the uuid again.
        """
        internal_id = self.__getattribute__("internal_id")
        if self.application.get_ws(internal_id) is not None:
            return

        notify_editor_change = False
        elect_live_leader = False
        try:
            with self.make_session() as session:
                entry = session.get(Session, internal_id)
                if entry:
                    if entry.is_editor or entry.is_cutting:
                        notify_editor_change = True
                    if entry.live_session:
                        elect_live_leader = True
                    session.delete(entry)
                    session.commit()
        except Exception:
            get_logger().exception(
                f"Error finalising disconnected session {internal_id} "
                f"({self.request.remote_ip})"
            )

        if notify_editor_change:
            for client in self.application.clients:
                client.write_message(
                    {"OP": "NOOP", "ACTION": "GET_SCRIPT_CONFIG_STATUS", "DATA": {}}
                )

        if elect_live_leader:
            self._elect_live_leader(internal_id)

    def _elect_live_leader(self, departed_id: str) -> None:
        """Hand live-show leadership on after the leader *departed_id* has gone.

        A candidate is a connected client of the show session's user that is not
        itself inside a reconnect grace window. Candidates are tried in connection
        order, so the result is deterministic. With no candidate, ``NO_LEADER`` is
        broadcast and ``last_client_internal_id`` records the departed leader so
        that it can reclaim leadership if it comes back later.

        :param departed_id: The uuid of the leader whose session was finalised.
        """
        show_setting = self.application.digi_settings.settings.get("current_show")
        if not show_setting:
            return
        current_show = show_setting.get_value()
        if not current_show:
            return

        with self.make_session() as session:
            show = session.get(Show, current_show)
            if not show or not show.current_session_id:
                return
            live_session: Optional[ShowSession] = session.get(
                ShowSession, show.current_session_id
            )
            if live_session is None:
                return
            if live_session.client_internal_id not in (None, departed_id):
                # Someone else already leads; leave them be.
                return

            live_session.last_client_internal_id = departed_id
            session.flush()

            next_ws = None
            if live_session.user_id is not None:
                candidate_ids = set(
                    session.scalars(
                        select(Session.internal_id).where(
                            Session.user_id == live_session.user_id,
                            Session.internal_id != departed_id,
                        )
                    ).all()
                )
                pending = self.application.pending_disconnects
                for client in self.application.clients:
                    client_id = getattr(client, "internal_id", None)
                    if client_id in candidate_ids and not pending.is_pending(client_id):
                        next_ws = client
                        break

            if next_ws is not None:
                live_session.client_internal_id = next_ws.__getattribute__(
                    "internal_id"
                )
                live_session.last_client_internal_id = None
                next_ws.write_message(
                    {
                        "OP": "NOOP",
                        "ACTION": "ELECTED_LEADER",
                        "DATA": {"latest_line_ref": live_session.latest_line_ref},
                    }
                )
            else:
                live_session.client_internal_id = None
                for client in self.application.clients:
                    client.write_message(
                        {"OP": "NOOP", "ACTION": "NO_LEADER", "DATA": {}}
                    )

            session.commit()
            for client in self.application.clients:
                client.write_message(
                    {"OP": "NOOP", "ACTION": "GET_SHOW_SESSION_DATA", "DATA": {}}
                )

    async def _close_room_if_editorless(self, room) -> None:
        """Close the collaborative-editing room if it still has no editors.

        Scheduled by :meth:`on_close` when the room's last editor disconnects, and
        run after the reconnect grace window. It is deliberately not cancelled by
        ``REFRESH_CLIENT``: if the reloaded editor rejoined in time the room has
        an editor again and this does nothing. Otherwise the room is checkpointed
        (if dirty) and closed, which is what happened immediately before the grace
        window existed. The draft survives in the checkpoint.

        :param room: The room the editor left.
        """
        room_manager = getattr(self.application, "room_manager", None)
        if (
            room_manager is None
            or room_manager.get_active_room() is not room
            or room.has_editors
        ):
            return
        try:
            if room._dirty:
                await room_manager._checkpoint_room(room)
                await self.application.ws_send_to_all(
                    "NOOP", "GET_SCRIPT_REVISIONS", {}
                )
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

    async def authenticate_with_token(self, token):
        """Authenticate using JWT token"""
        is_revoked = await self.application.jwt_service.is_token_revoked(token)
        if is_revoked:
            await self.write_message({"OP": "WS_AUTH_ERROR", "DATA": "Revoked token"})
            return False

        payload = self.application.jwt_service.decode_access_token(token)
        if not payload or "user_id" not in payload:
            await self.write_message(
                {"OP": "WS_AUTH_ERROR", "DATA": "Invalid or expired token"}
            )
            return False

        if not self.application.jwt_service.validate_token_age(payload):
            await self.write_message(
                {"OP": "WS_AUTH_ERROR", "DATA": "Token expired (lifetime exceeded)"}
            )
            return False

        with self.make_session() as session:
            user = session.get(User, int(payload["user_id"]))
            if not user:
                await self.write_message(
                    {"OP": "WS_AUTH_ERROR", "DATA": "User not found"}
                )
                return False

            # Update the user ID for this connection
            self.current_user_id = user.id
            self.current_username = user.username
            get_logger().info(
                f"WebSocket authenticated: {user.username} from {self.request.remote_ip}"
            )

            # Update the session with the user ID
            self.update_session(user_id=user.id)

            # Notify of successful authentication
            await self.write_message(
                {
                    "OP": "WS_AUTH_SUCCESS",
                    "DATA": {"user_id": user.id, "username": user.username},
                }
            )
            return True

    async def on_message(self, message: Union[str, bytes]):
        user_part = (
            f"{self.current_username} ({self.request.remote_ip})"
            if self.current_username
            else self.request.remote_ip
        )
        get_logger().debug(f"WebSocket message from {user_part}: {message}")

        try:
            message = json.loads(message)
            ws_op = message["OP"]
        except (json.JSONDecodeError, KeyError) as e:
            get_logger().warning(
                f"Malformed WS message from {self.request.remote_ip}: {e}"
            )
            return

        # Handle JWT authentication operations
        if ws_op == "AUTHENTICATE":
            token = message.get("DATA", {}).get("token")
            if token:
                await self.authenticate_with_token(token)
            else:
                await self.write_message(
                    {"OP": "WS_AUTH_ERROR", "DATA": "No token provided"}
                )
            return
        if ws_op == "REFRESH_TOKEN":
            token = message.get("DATA", {}).get("token")
            if token:
                success = await self.authenticate_with_token(token)
                if success:
                    await self.write_message(
                        {"OP": "WS_TOKEN_REFRESH_SUCCESS", "DATA": {}}
                    )
            else:
                await self.write_message(
                    {"OP": "WS_AUTH_ERROR", "DATA": "No token provided"}
                )
            return

        # Handle script room and collaborative editing operations
        if ws_op in (
            "JOIN_SCRIPT_ROOM",
            "LEAVE_SCRIPT_ROOM",
            "YJS_SYNC",
            "YJS_UPDATE",
            "YJS_AWARENESS",
            "SAVE_SCRIPT_DRAFT",
            "DISCARD_SCRIPT_DRAFT",
            "REQUEST_SCRIPT_EDIT",
            "REQUEST_SCRIPT_CUTS",
            "STOP_SCRIPT_EDIT",
        ):
            await self._handle_script_room_op(ws_op, message)
            return

        with self.make_session() as session:
            entry: Session = session.get(Session, self.__getattribute__("internal_id"))
            current_show = await self.application.digi_settings.get("current_show")
            if current_show:
                show = session.get(Show, current_show)
            else:
                show = None
            show_session: Optional[ShowSession] = None

            if ws_op == "NEW_CLIENT":
                if self.current_user_id and show and show.current_session_id:
                    show_session = session.get(ShowSession, show.current_session_id)
                    if show_session and not show_session.client_internal_id:
                        if show_session.user_id == self.current_user_id:
                            show_session.client_internal_id = self.__getattribute__(
                                "internal_id"
                            )
                            # A fresh leader supersedes any earlier leader's claim
                            # to reclaim on reconnect (same as election does).
                            show_session.last_client_internal_id = None
                            session.commit()
                            await self.write_message(
                                {
                                    "OP": "NOOP",
                                    "ACTION": "ELECTED_LEADER",
                                    "DATA": {
                                        "latest_line_ref": show_session.latest_line_ref
                                    },
                                }
                            )
                            await self.application.ws_send_to_all(
                                "NOOP", "GET_SHOW_SESSION_DATA", {}
                            )
            elif ws_op == "REFRESH_CLIENT":
                await self._resume_client(session, entry, show, message.get("DATA"))
            elif ws_op == "SCRIPT_SCROLL":
                if show and show.current_session_id:
                    show_session = session.get(ShowSession, show.current_session_id)
                    if show_session:
                        if show_session.client_internal_id == self.__getattribute__(
                            "internal_id"
                        ):
                            show_session.latest_line_ref = message["DATA"][
                                "current_line"
                            ]
                            session.commit()
                            await self.application.ws_send_to_all(
                                "NOOP", "SCRIPT_SCROLL", message["DATA"]
                            )
            elif ws_op == "BEGIN_INTERVAL":
                if show and show.current_session_id:
                    show_session = session.get(ShowSession, show.current_session_id)
                    if show_session:
                        if show_session.client_internal_id == self.__getattribute__(
                            "internal_id"
                        ):
                            act: Act = session.get(Act, message["DATA"]["actId"])
                            if not entry:
                                return

                            show_interval = Interval(
                                session_id=show_session.id,
                                act_id=act.id,
                                initial_length=message["DATA"]["length"],
                            )
                            session.add(show_interval)
                            session.flush()
                            show_session.current_interval_id = show_interval.id
                            session.commit()
                            await self.application.ws_send_to_all(
                                "NOOP", "GET_SHOW_SESSION_DATA", {}
                            )
            elif ws_op == "END_INTERVAL":
                if show and show.current_session_id:
                    show_session = session.get(ShowSession, show.current_session_id)
                    if show_session:
                        if show_session.client_internal_id == self.__getattribute__(
                            "internal_id"
                        ):
                            current_interval: Interval = session.get(
                                Interval, show_session.current_interval_id
                            )
                            if current_interval:
                                current_interval.end_datetime = datetime.datetime.now(
                                    tz=datetime.timezone.utc
                                )
                            show_session.current_interval_id = None
                            session.commit()
                            await self.application.ws_send_to_all(
                                "NOOP", "GET_SHOW_SESSION_DATA", {}
                            )
            elif ws_op == "RELOAD_CLIENTS":
                if show and show.current_session_id:
                    show_session = session.get(ShowSession, show.current_session_id)
                    if (
                        show_session
                        and show_session.client_internal_id
                        == self.__getattribute__("internal_id")
                    ):
                        await self.application.ws_send_to_all(
                            "RELOAD_CLIENT", "NOOP", {}
                        )
            elif ws_op == "LIVE_SHOW_JUMP_TO_PAGE":
                if show and show.current_session_id:
                    show_session = session.get(ShowSession, show.current_session_id)
                    if show_session:
                        show_session.latest_line_ref = (
                            f"page_{message['DATA']['page']}_line_0"
                        )
                        session.commit()
                        await self.application.ws_send_to_all(
                            "RELOAD_CLIENT", "NOOP", {}
                        )
            else:
                get_logger().warning(
                    f"Unknown OP {ws_op} received from "
                    f"WebSocket connection {self.request.remote_ip}"
                )

    async def _resume_client(
        self,
        session,
        placeholder: Optional[Session],
        show: Optional[Show],
        new_uuid: Any,
    ) -> None:
        """Handle ``REFRESH_CLIENT``: a reconnecting page resumes its old uuid.

        Cancels the old uuid's pending disconnect finalisation, discards the
        placeholder row that :meth:`open` created for this connection, and
        adopts the old uuid's Session row as-is, keeping its edit/cut flags. The
        row still holds live-show leadership if the reconnect happened inside the
        grace window. If the window had already expired and the leader was
        released with nobody else promoted, leadership is reclaimed here, but
        only while no one else holds it.

        :param session: Active SQLAlchemy session.
        :param placeholder: This connection's placeholder Session row, if any.
        :param show: The currently loaded Show, or None.
        :param new_uuid: The uuid the client asks to resume.
        """
        if not isinstance(new_uuid, str) or not new_uuid:
            get_logger().warning(
                f"REFRESH_CLIENT with invalid uuid from {self.request.remote_ip}"
            )
            return
        if new_uuid == self.__getattribute__("internal_id"):
            return

        was_pending = self.application.pending_disconnects.cancel(new_uuid)

        if placeholder is not None:
            session.delete(placeholder)
            session.flush()
        self.__setattr__("internal_id", new_uuid)

        entry = session.get(Session, new_uuid)
        if entry is None:
            session.add(
                Session(
                    internal_id=new_uuid,
                    remote_ip=self.request.remote_ip,
                    last_ping=self._last_ping,
                    last_pong=self._last_pong,
                    user_id=self.current_user_id,
                )
            )
        else:
            entry.remote_ip = self.request.remote_ip
            entry.last_ping = self._last_ping
            entry.last_pong = self._last_pong
            self._assign_session_user(entry, self.current_user_id)
        session.commit()
        get_logger().info(
            f"WebSocket from {self.request.remote_ip} resumed client {new_uuid} "
            f"({'within grace window' if was_pending else 'no pending disconnect'}"
            f"{', session state restored' if entry is not None else ''})"
        )

        if show and show.current_session_id:
            show_session = session.get(ShowSession, show.current_session_id)
            if (
                show_session
                and show_session.client_internal_id is None
                and show_session.last_client_internal_id == new_uuid
            ):
                show_session.client_internal_id = new_uuid
                show_session.last_client_internal_id = None
                session.commit()
                await self.application.ws_send_to_all(
                    "NOOP", "GET_SHOW_SESSION_DATA", {}
                )

    async def _is_live_session_active(self) -> bool:
        """Return True if a show session is currently running.

        :returns: True if the current show has an active session, False otherwise.
        """
        current_show_id = await self.application.digi_settings.get("current_show")
        if not current_show_id:
            return False
        with self.make_session() as session:
            show = session.get(Show, current_show_id)
            return bool(show and show.current_session_id)

    def _is_collab_editing_enabled(self) -> bool:
        """Return True if the server is in collaborative script editing mode.

        :returns: The collaborative script editing setting.
        """
        return bool(self.application.digi_settings.get_sync(COLLAB_EDITING_SETTING))

    async def _get_current_show(self, session) -> Optional[Show]:
        """Look up the currently-loaded Show, if any.

        :param session: Active SQLAlchemy session.
        :returns: The current Show, or None if no show is loaded.
        """
        current_show_id = await self.application.digi_settings.get("current_show")
        return session.get(Show, current_show_id) if current_show_id else None

    def _user_has_script_write_access(self, session, show: Optional[Show]) -> bool:
        """Return True if the connected user is an admin or has WRITE on *show*.

        :param session: Active SQLAlchemy session.
        :param show: The current Show, or None.
        :returns: True if the user may request script edit/cuts access.
        """
        user = session.get(User, self.current_user_id) if self.current_user_id else None
        if not user:
            return False
        return user.is_admin or bool(
            show and self.application.rbac.has_role(user, show, Role.WRITE)
        )

    async def _reject_script_room_op(self, action: str, key: str, reason: str) -> None:
        """Send a script-room-op failure message.

        :param action: The ACTION value to send (e.g. ``REQUEST_EDIT_FAILURE``).
        :param key: The DATA key to carry the reason (``"reason"`` or ``"error"``).
        :param reason: The human-readable failure reason.
        """
        await self.write_message(
            {"OP": "NOOP", "ACTION": action, "DATA": {key: reason}}
        )

    async def _require_editor_write_access(self, session, entry) -> bool:
        """Verify the session is an active editor with WRITE permission.

        Used by ``SAVE_SCRIPT_DRAFT`` / ``DISCARD_SCRIPT_DRAFT``, which both require
        the requester to already hold editor status on top of RBAC WRITE. Sends a
        ``COLLAB_ERROR`` and returns False on failure.

        :param session: Active SQLAlchemy session.
        :param entry: The requester's Session row, or None.
        :returns: True if the requester may proceed.
        """
        if entry is None or not entry.is_editor:
            await self._reject_script_room_op(
                "COLLAB_ERROR", "error", ERROR_INSUFFICIENT_PERMISSIONS
            )
            return False
        show = await self._get_current_show(session)
        if not self._user_has_script_write_access(session, show):
            await self._reject_script_room_op(
                "COLLAB_ERROR", "error", ERROR_INSUFFICIENT_PERMISSIONS
            )
            return False
        return True

    async def _handle_script_room_op(self, ws_op: str, message: dict):
        """Handle script room and collaborative editing WebSocket operations.

        :param ws_op: The operation code.
        :param message: The full parsed message dict.
        """
        room_manager = getattr(self.application, "room_manager", None)
        if not room_manager:
            get_logger().warning("RoomManager not available, ignoring collab OP")
            return

        data = message.get("DATA", {})

        # Everything that touches the shared draft only exists in collaborative mode;
        # in classic mode a stray client must not be able to open a room.
        # LEAVE_SCRIPT_ROOM stays allowed (harmless, and lets a client tidy up after
        # the mode is switched underneath it).
        if ws_op in _COLLAB_ONLY_OPS and not self._is_collab_editing_enabled():
            await self._reject_script_room_op(
                "COLLAB_ERROR", "error", ERROR_COLLAB_EDITING_DISABLED
            )
            return

        if ws_op == "REQUEST_SCRIPT_EDIT":
            with self.make_session() as session:
                entry = session.get(Session, self.__getattribute__("internal_id"))
                if entry is None:
                    get_logger().warning(
                        "REQUEST_SCRIPT_EDIT: session entry not found "
                        "(race with on_close?)"
                    )
                    return
                show = await self._get_current_show(session)

                if show and show.current_session_id:
                    await self._reject_script_room_op(
                        "REQUEST_EDIT_FAILURE",
                        "reason",
                        ERROR_EDIT_BLOCKED_BY_LIVE_SESSION,
                    )
                    return

                if not self._user_has_script_write_access(session, show):
                    await self._reject_script_room_op(
                        "REQUEST_EDIT_FAILURE",
                        "reason",
                        ERROR_INSUFFICIENT_PERMISSIONS,
                    )
                    return

                # The collaborative editor announces itself with `collab: true`.
                # Requiring the announcement to match the server's mode means an
                # old-UI client is refused up front in collaborative mode, instead of
                # letting it edit and then fail (and lose its work) at save time.
                collab_enabled = self._is_collab_editing_enabled()
                # An explicit boolean is required so a client that omits the flag
                # (a stale UI, or cut mode) is never mistaken for a collab request.
                if data.get("collab", False) is not collab_enabled:
                    await self._reject_script_room_op(
                        "REQUEST_EDIT_FAILURE",
                        "reason",
                        ERROR_COLLAB_EDITING_ENABLED
                        if collab_enabled
                        else ERROR_COLLAB_EDITING_DISABLED,
                    )
                    return

                cutters = session.scalars(
                    select(Session).where(Session.is_cutting)
                ).all()
                if cutters:
                    await self.write_message(
                        {
                            "OP": "NOOP",
                            "ACTION": "REQUEST_EDIT_FAILURE",
                            "DATA": {"reason": ERROR_EDIT_BLOCKED_BY_CUTTER},
                        }
                    )
                    return

                # Classic (REST) editing has no way to reconcile concurrent writers,
                # so it stays single-editor; only collaborative mode allows several.
                if not collab_enabled:
                    other_editors = session.scalars(
                        select(Session).where(
                            Session.is_editor,
                            Session.internal_id != self.__getattribute__("internal_id"),
                        )
                    ).all()
                    if other_editors:
                        await self._reject_script_room_op(
                            "REQUEST_EDIT_FAILURE",
                            "reason",
                            ERROR_EDIT_BLOCKED_BY_EDITOR,
                        )
                        return

                entry.is_editor = True
                session.commit()

            room = room_manager.get_room_for_client(self)
            if room:
                room.add_client(self, "editor")
                with self.make_session() as session:
                    await room.broadcast_members(session)

            await self.application.ws_send_to_all(
                "NOOP", "GET_SCRIPT_CONFIG_STATUS", {}
            )
        elif ws_op == "REQUEST_SCRIPT_CUTS":
            with self.make_session() as session:
                entry = session.get(Session, self.__getattribute__("internal_id"))
                if entry is None:
                    get_logger().warning(
                        "REQUEST_SCRIPT_CUTS: session entry not found "
                        "(race with on_close?)"
                    )
                    return
                show = await self._get_current_show(session)

                if show and show.current_session_id:
                    await self._reject_script_room_op(
                        "REQUEST_EDIT_FAILURE",
                        "reason",
                        ERROR_EDIT_BLOCKED_BY_LIVE_SESSION,
                    )
                    return

                if not self._user_has_script_write_access(session, show):
                    await self._reject_script_room_op(
                        "REQUEST_EDIT_FAILURE",
                        "reason",
                        ERROR_INSUFFICIENT_PERMISSIONS,
                    )
                    return

                cutters = session.scalars(
                    select(Session).where(
                        Session.is_cutting,
                        Session.internal_id != self.__getattribute__("internal_id"),
                    )
                ).all()
                if cutters:
                    await self.write_message(
                        {
                            "OP": "NOOP",
                            "ACTION": "REQUEST_EDIT_FAILURE",
                            "DATA": {"reason": ERROR_CUTS_BLOCKED_BY_CUTTER},
                        }
                    )
                    return

                editors = session.scalars(
                    select(Session).where(Session.is_editor)
                ).all()
                if editors:
                    await self.write_message(
                        {
                            "OP": "NOOP",
                            "ACTION": "REQUEST_EDIT_FAILURE",
                            "DATA": {"reason": ERROR_CUTS_BLOCKED_BY_EDITOR},
                        }
                    )
                    return

                if show:
                    script = session.scalar(
                        select(Script).where(Script.show_id == show.id)
                    )
                    if script and script.current_revision:
                        if await room_manager.has_unsaved_changes():
                            await self.write_message(
                                {
                                    "OP": "NOOP",
                                    "ACTION": "REQUEST_EDIT_FAILURE",
                                    "DATA": {"reason": ERROR_CUTS_BLOCKED_BY_DRAFT},
                                }
                            )
                            return

                entry.is_cutting = True
                session.commit()

            await self.application.ws_send_to_all(
                "NOOP", "GET_SCRIPT_CONFIG_STATUS", {}
            )
        elif ws_op == "STOP_SCRIPT_EDIT":
            with self.make_session() as session:
                entry = session.get(Session, self.__getattribute__("internal_id"))
                if entry and (entry.is_editor or entry.is_cutting):
                    entry.is_editor = False
                    entry.is_cutting = False
                    session.commit()

            room = room_manager.get_room_for_client(self)
            if room:
                room.add_client(self, "viewer")
                with self.make_session() as session:
                    await room.broadcast_members(session)
                if not room.has_editors:
                    if room._dirty:
                        await room_manager._checkpoint_room(room)
                        await self.application.ws_send_to_all(
                            "NOOP", "GET_SCRIPT_REVISIONS", {}
                        )
                    await room_manager.close_active_room()

            await self.application.ws_send_to_all(
                "NOOP", "GET_SCRIPT_CONFIG_STATUS", {}
            )
        elif ws_op == "JOIN_SCRIPT_ROOM":
            # Server-side revision lookup: the client never needs to tell us which
            # revision to join — there is only ever one active revision.
            current_show_id = await self.application.digi_settings.get("current_show")
            if not current_show_id:
                await self.write_message(
                    {
                        "OP": "NOOP",
                        "ACTION": "COLLAB_ERROR",
                        "DATA": {"error": "No show loaded"},
                    }
                )
                return
            with self.make_session() as lookup_session:
                show_obj = lookup_session.get(Show, current_show_id)
                script_obj = (
                    lookup_session.scalar(
                        select(Script).where(Script.show_id == show_obj.id)
                    )
                    if show_obj
                    else None
                )
                revision_id = script_obj.current_revision if script_obj else None
            if not revision_id:
                await self.write_message(
                    {
                        "OP": "NOOP",
                        "ACTION": "COLLAB_ERROR",
                        "DATA": {"error": "No active revision"},
                    }
                )
                return

            # Guard: block joining a room during a live show session
            if await self._is_live_session_active():
                await self.write_message(
                    {
                        "OP": "NOOP",
                        "ACTION": "COLLAB_ERROR",
                        "DATA": {"error": ERROR_EDIT_BLOCKED_BY_LIVE_SESSION},
                    }
                )
                return

            # Determine role from the session's is_editor flag (set authoritatively
            # by REQUEST_SCRIPT_EDIT which runs full RBAC enforcement).
            role = "viewer"
            if self.current_user_id:
                with self.make_session() as role_session:
                    ws_session = role_session.get(
                        Session, self.__getattribute__("internal_id")
                    )
                    if ws_session and ws_session.is_editor:
                        role = "editor"

            try:
                room = await room_manager.get_or_create_room(revision_id)
            except Exception:
                get_logger().exception(
                    f"Failed to build/load Y.Doc for revision {revision_id}"
                )
                await self.write_message(
                    {
                        "OP": "NOOP",
                        "ACTION": "COLLAB_ERROR",
                        "DATA": {"error": "Failed to open script for editing"},
                    }
                )
                return
            room.add_client(self, role)

            # Send initial sync: full document state
            sync_state = room.get_sync_state()
            await self.write_message(
                {
                    "OP": "NOOP",
                    "ACTION": "YJS_SYNC",
                    "DATA": {
                        "step": 0,
                        "payload": base64.b64encode(sync_state).decode("ascii"),
                    },
                }
            )

            # Broadcast updated member list to all room clients
            with self.make_session() as session:
                await room.broadcast_members(session)

            # Notify all clients about the new collaborator
            await self.application.ws_send_to_all(
                "NOOP", "GET_SCRIPT_CONFIG_STATUS", {}
            )
        elif ws_op == "LEAVE_SCRIPT_ROOM":
            room = room_manager.get_room_for_client(self)
            if room:
                room.remove_client(self)
                # Broadcast updated member list to remaining clients
                with self.make_session() as session:
                    await room.broadcast_members(session)
                await self.application.ws_send_to_all(
                    "NOOP", "GET_SCRIPT_CONFIG_STATUS", {}
                )
        elif ws_op == "YJS_SYNC":
            room = room_manager.get_room_for_client(self)
            if not room:
                return

            payload = data.get("payload", "")
            step = data.get("step", 1)

            try:
                decoded = base64.b64decode(payload)
            except Exception:
                get_logger().warning("Invalid base64 in YJS_SYNC message")
                return

            if step == 1:
                # Client sends its state vector; server responds with diff
                get_logger().trace(
                    f"YJS_SYNC step=1 rev={room.revision_id} "
                    f"state-vector {len(decoded)}B from {self.request.remote_ip}"
                )
                diff = room.get_update_for(decoded)
                get_logger().trace(
                    f"YJS_SYNC step=2 rev={room.revision_id} "
                    f"sending diff {len(diff)}B to {self.request.remote_ip}"
                )
                await self.write_message(
                    {
                        "OP": "NOOP",
                        "ACTION": "YJS_SYNC",
                        "DATA": {
                            "step": 2,
                            "payload": base64.b64encode(diff).decode("ascii"),
                        },
                    }
                )
            elif step == 2:
                # Client sends its diff; server applies it
                if room.clients.get(self) != "editor":
                    await self._reject_script_room_op(
                        "COLLAB_ERROR", "error", ERROR_INSUFFICIENT_PERMISSIONS
                    )
                    return
                if await self._is_live_session_active():
                    await self.write_message(
                        {
                            "OP": "NOOP",
                            "ACTION": "COLLAB_ERROR",
                            "DATA": {"error": ERROR_EDIT_BLOCKED_BY_LIVE_SESSION},
                        }
                    )
                    return
                get_logger().trace(
                    f"YJS_SYNC step=2 rev={room.revision_id} "
                    f"applying {len(decoded)}B update from {self.request.remote_ip}"
                )
                try:
                    follow_up = await room.apply_update(decoded)
                except Exception:
                    get_logger().exception(
                        f"YJS_SYNC step=2: Failed to apply update for "
                        f"revision {room.revision_id}"
                    )
                    await self.write_message(
                        {
                            "OP": "NOOP",
                            "ACTION": "COLLAB_ERROR",
                            "DATA": {"error": "Failed to apply document sync update"},
                        }
                    )
                    return
                await room.broadcast_update(decoded, sender=self)
                if follow_up:
                    await room.broadcast_update(follow_up)
        elif ws_op == "YJS_UPDATE":
            room = room_manager.get_room_for_client(self)
            if not room:
                return

            if room.clients.get(self) != "editor":
                await self._reject_script_room_op(
                    "COLLAB_ERROR", "error", ERROR_INSUFFICIENT_PERMISSIONS
                )
                return

            payload = data.get("payload", "")
            try:
                decoded = base64.b64decode(payload)
            except Exception:
                get_logger().warning("Invalid base64 in YJS_UPDATE message")
                return

            if await self._is_live_session_active():
                await self.write_message(
                    {
                        "OP": "NOOP",
                        "ACTION": "COLLAB_ERROR",
                        "DATA": {"error": ERROR_EDIT_BLOCKED_BY_LIVE_SESSION},
                    }
                )
                return

            get_logger().trace(
                f"YJS_UPDATE rev={room.revision_id} "
                f"applying {len(decoded)}B update from {self.request.remote_ip}"
            )
            try:
                follow_up = await room.apply_update(decoded)
            except Exception:
                await self.write_message(
                    {
                        "OP": "NOOP",
                        "ACTION": "COLLAB_ERROR",
                        "DATA": {"error": "Failed to apply document update"},
                    }
                )
                return
            await room.broadcast_update(decoded, sender=self)
            if follow_up:
                # The server-made trailing page goes to everyone, sender included.
                await room.broadcast_update(follow_up)
        elif ws_op == "YJS_AWARENESS":
            room = room_manager.get_room_for_client(self)
            if not room:
                return

            payload = data.get("payload", "")
            try:
                decoded = base64.b64decode(payload)
            except Exception:
                get_logger().warning("Invalid base64 in YJS_AWARENESS message")
                return

            await room.broadcast_awareness(decoded, sender=self)
        elif ws_op == "SAVE_SCRIPT_DRAFT":
            if await self._is_live_session_active():
                await self.write_message(
                    {
                        "OP": "NOOP",
                        "ACTION": "COLLAB_ERROR",
                        "DATA": {"error": ERROR_EDIT_BLOCKED_BY_LIVE_SESSION},
                    }
                )
                return
            with self.make_session() as session:
                entry = session.get(Session, self.__getattribute__("internal_id"))
                if not await self._require_editor_write_access(session, entry):
                    return
            await room_manager.save_room(self)
            await self.application.ws_send_to_all("NOOP", "GET_SCRIPT_REVISIONS", {})
        elif ws_op == "DISCARD_SCRIPT_DRAFT":
            # Not blocked by a live session: discarding is the only recovery path if a
            # live session starts while a draft is open, so it must stay reachable.
            with self.make_session() as session:
                entry = session.get(Session, self.__getattribute__("internal_id"))
                if not await self._require_editor_write_access(session, entry):
                    return
            await room_manager.discard_room(self)
            await self.application.ws_send_to_all(
                "NOOP", "GET_SCRIPT_CONFIG_STATUS", {}
            )
            await self.application.ws_send_to_all("NOOP", "GET_SCRIPT_REVISIONS", {})

    def on_pong(self, data: bytes) -> None:
        self._last_pong = IOLoop.current().time()
        self.update_session()
        get_logger().trace(
            f"Ping response from {self.request.remote_ip} : {data.hex()}"
        )

    def on_ping(self, data: bytes) -> None:
        self._last_ping = IOLoop.current().time()
        self.update_session()
        get_logger().trace(f"Ping from {self.request.remote_ip} : {data.hex()}")

    @gen.coroutine
    def write_message(
        self, message: Union[bytes, str, Dict[str, Any]], binary: bool = False
    ) -> Future[None]:
        try:
            return super().write_message(message, binary)
        except WebSocketClosedError:
            get_logger().error(
                f"Trying to send message to closed websocket "
                f"{self.__getattribute__('internal_id')} at IP address "
                f"{self.request.remote_ip}, closing."
            )
            self.on_close()
            return None
