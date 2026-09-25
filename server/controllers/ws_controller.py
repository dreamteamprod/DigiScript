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
from utils.web.pending_disconnects import disconnect_key
from utils.web.route import ApiRoute, ApiVersion
from utils.web.ws_session_lifecycle import (
    assign_session_user,
    broadcast,
    get_live_session,
    owner_is_connected,
    release_session_privileges,
    row_owner,
    safe_write,
    schedule_disconnect_deadline,
    schedule_room_close,
)


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
    # Live-show ops only the leader may send, and the method that handles each.
    _LEADER_OP_HANDLERS = {
        "SCRIPT_SCROLL": "_op_script_scroll",
        "BEGIN_INTERVAL": "_op_begin_interval",
        "END_INTERVAL": "_op_end_interval",
        "RELOAD_CLIENTS": "_op_reload_clients",
    }

    # Script room / collaborative editing ops and the method that handles each.
    _SCRIPT_ROOM_OP_HANDLERS = {
        "REQUEST_SCRIPT_EDIT": "_op_request_script_edit",
        "REQUEST_SCRIPT_CUTS": "_op_request_script_cuts",
        "STOP_SCRIPT_EDIT": "_op_stop_script_edit",
        "JOIN_SCRIPT_ROOM": "_op_join_script_room",
        "LEAVE_SCRIPT_ROOM": "_op_leave_script_room",
        "YJS_SYNC": "_op_yjs_sync",
        "YJS_UPDATE": "_op_yjs_update",
        "YJS_AWARENESS": "_op_yjs_awareness",
        "SAVE_SCRIPT_DRAFT": "_op_save_script_draft",
        "DISCARD_SCRIPT_DRAFT": "_op_discard_script_draft",
    }

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
        # The uuid open() created; REFRESH_CLIENT deletes only this row.
        self._placeholder_id: Optional[str] = None
        # A connection may resume a uuid via REFRESH_CLIENT at most once.
        self._resumed = False

    def update_session(self, user_id=None) -> bool:
        """Create or refresh the Session row for this connection's uuid.

        Edit/cut flags are never *granted* here (only ``REQUEST_SCRIPT_EDIT`` /
        ``REQUEST_SCRIPT_CUTS`` grant them). They are cleared if the row changes
        hands to a different user, see :func:`assign_session_user`.

        :param user_id: Authenticated user id, or None to leave it unchanged.
        :returns: True if edit/cut flags were cleared; the caller broadcasts.
        """
        cleared = False
        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__("internal_id"))
            if entry:
                entry.last_ping = self._last_ping
                entry.last_pong = self._last_pong
                cleared = assign_session_user(entry, user_id)
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
        return cleared

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(f"Data streaming not supported for {self.__class__}")

    def check_origin(self, origin):
        if self.settings.get("debug", False):
            return True
        return super().check_origin(origin)

    @gen.coroutine
    def open(self, *args: str, **kwargs: str) -> Optional[Awaitable[None]]:
        self.__setattr__("internal_id", str(uuid4()))
        self._placeholder_id = self.__getattribute__("internal_id")
        self.application.clients.append(self)

        self.update_session(user_id=self.current_user_id)
        get_logger().info(f"WebSocket opened from: {self.request.remote_ip}")

        yield self.write_message(
            {"OP": "SET_UUID", "DATA": self.__getattribute__("internal_id")}
        )
        yield self.write_message({"OP": "NOOP", "DATA": {}, "ACTION": "GET_SETTINGS"})

    def on_close(self) -> None:
        """Handle the socket closing, without treating the close as final.

        Tornado calls this when the socket drops, and ``write_message`` calls it
        again if a write finds the socket closed, so it only acts once per
        handler. If a connection authenticated as the row's owner still holds
        this uuid (the owner's reloaded tab, or another of its same-browser
        tabs), nothing is released. Otherwise the uuid's grace deadline starts
        (see :func:`schedule_disconnect_deadline`), unless one is already
        running, in which case the original deadline is kept. At the deadline
        :func:`finalise_disconnect` releases the Session row, its edit/cut lock
        and live-show leadership, unless the owner has authenticated again by
        then. The handler leaves any collaborative-editing room immediately. If
        it was the room's last editor, :func:`close_room_if_editorless` runs after
        the window (not cancelled; it does nothing if an editor has rejoined).
        See issue #1419.
        """
        if self._close_handled:
            return
        self._close_handled = True

        if self in self.application.clients:
            self.application.clients.remove(self)
        self._leave_room()

        internal_id = getattr(self, "internal_id", None)
        user_part = (
            f"{self.current_username} ({self.request.remote_ip})"
            if self.current_username
            else self.request.remote_ip
        )
        if internal_id is None:
            get_logger().info(f"WebSocket closed from: {user_part}")
            return

        try:
            _, owner_id = row_owner(self.application, internal_id)
        except Exception:
            get_logger().exception(f"Could not read the row of client {internal_id}")
            owner_id = None
        if owner_is_connected(self.application, internal_id, owner_id):
            get_logger().info(
                f"WebSocket closed from: {user_part} (client {internal_id} is still "
                f"connected as its owner; nothing to release)"
            )
            return

        registry = self.application.pending_disconnects
        if schedule_disconnect_deadline(self.application, internal_id):
            get_logger().info(
                f"WebSocket closed from: {user_part} (client {internal_id} held for "
                f"{registry.grace_seconds:g}s reconnect grace window)"
            )
        else:
            get_logger().info(
                f"WebSocket closed from: {user_part} (client {internal_id} keeps "
                f"its original grace deadline)"
            )

    def _leave_room(self) -> None:
        """Remove this (closed) handler from the collaborative-editing room.

        If it was the room's last editor, closing the room is deferred to the end
        of the grace window, so a reloading editor that rejoins in time keeps the
        room and its viewers never see ``ROOM_CLOSED``.
        """
        room_manager = getattr(self.application, "room_manager", None)
        room = room_manager.get_room_for_client(self) if room_manager else None
        if room is None:
            return
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
            schedule_room_close(app, room)

    # ------------------------------------------------------------------
    # Ownership: a uuid is identity, not a credential
    # ------------------------------------------------------------------

    def _owned_row(self, session) -> Optional[Session]:
        """Return this connection's Session row if the connection owns it.

        The ownership rule: the edit/cut lock and leadership recorded against a
        uuid may only be used by a connection authenticated as the row's owner.

        :param session: Active SQLAlchemy session.
        :returns: The row, or None if it is missing or owned by someone else (or
            this connection is not authenticated).
        """
        if self.current_user_id is None:
            return None
        entry = session.get(Session, self.__getattribute__("internal_id"))
        if entry is None or entry.user_id != self.current_user_id:
            return None
        return entry

    def _is_leader(self, session, show_session: Optional[ShowSession]) -> bool:
        """Return True if this connection may act as the live-show leader.

        Requires the uuid to hold leadership, the connection to be authenticated
        as the show session's user, and the row to be owned by that user.

        :param session: Active SQLAlchemy session.
        :param show_session: The running show session, or None.
        """
        return (
            show_session is not None
            and show_session.client_internal_id == self.__getattribute__("internal_id")
            and show_session.user_id is not None
            and show_session.user_id == self.current_user_id
            and self._owned_row(session) is not None
        )

    def _reconcile_after_auth(self, user_id: int) -> None:
        """Settle who owns this connection's uuid once it has authenticated.

        * No row: a row owned by *user_id* is created.
        * Owned by *user_id*: the owner is back. Its grace deadline (if any) is
          cancelled and its lock and leadership carry on.
        * Owned by someone else who is still connected as its owner (a shared or
          presented uuid): the row is left alone and this connection gets no
          privileges.
        * Owned by someone else whose grace deadline is running: left alone
          until the deadline decides (see :func:`finalise_disconnect`).
        * No owner, or an owner that is gone with no deadline pending (this same
          socket switching user): *user_id* takes the client over. Anything the
          old owner held is released, with the usual broadcasts.
        * Finally, a departed leader coming back after its deadline reclaims
          leadership (see :meth:`_reclaim_leadership`).

        :param user_id: The authenticated user.
        """
        internal_id = self.__getattribute__("internal_id")
        registry = self.application.pending_disconnects
        exists, owner_id = row_owner(self.application, internal_id)

        if not exists or owner_id == user_id:
            self.update_session(user_id=user_id)
            if registry.cancel(disconnect_key(internal_id)):
                get_logger().info(
                    f"Client {internal_id} is back as its owner; grace deadline "
                    f"cancelled"
                )
        elif owner_is_connected(
            self.application, internal_id, owner_id, exclude=self
        ) or registry.is_pending(internal_id):
            get_logger().info(
                f"Client {internal_id} is owned by user {owner_id}, not {user_id}; "
                f"this connection gets none of its privileges"
            )
            self.update_session()
            return
        else:
            release_session_privileges(
                self.application, internal_id, f"taken over by user {user_id}"
            )
            if self.update_session(user_id=user_id):
                broadcast(self.application, "GET_SCRIPT_CONFIG_STATUS")
        self._reclaim_leadership(user_id)

    def _reclaim_leadership(self, user_id: int) -> None:
        """Give leadership back to a departed leader that authenticated again.

        :param user_id: The authenticated user.
        """
        internal_id = self.__getattribute__("internal_id")
        with self.make_session() as session:
            live_session = get_live_session(self.application, session)
            if (
                live_session is None
                or live_session.client_internal_id is not None
                or live_session.last_client_internal_id != internal_id
                or live_session.user_id != user_id
                # Defence in depth: reconcile only reaches here once the row is
                # owned by user_id, so this check cannot fail today.
                or self._owned_row(session) is None
            ):
                return
            live_session.client_internal_id = internal_id
            live_session.last_client_internal_id = None
            latest_line_ref = live_session.latest_line_ref
            session.commit()
        get_logger().info(f"Client {internal_id} reclaimed live-show leadership")
        safe_write(
            self,
            {
                "OP": "NOOP",
                "ACTION": "ELECTED_LEADER",
                "DATA": {"latest_line_ref": latest_line_ref},
            },
        )
        broadcast(self.application, "GET_SHOW_SESSION_DATA")

    async def authenticate_with_token(self, token):
        """Authenticate using a JWT token.

        A failed authentication changes nothing on the row: the connection simply
        stays unauthenticated and so cannot use any privilege recorded against
        its uuid.

        :param token: The JWT access token.
        :returns: True on success.
        """
        user = await self._user_for_token(token)
        if user is None:
            return False

        self.current_user_id = user.id
        self.current_username = user.username
        get_logger().info(
            f"WebSocket authenticated: {user.username} from {self.request.remote_ip}"
        )
        self._reconcile_after_auth(user.id)

        await self.write_message(
            {
                "OP": "WS_AUTH_SUCCESS",
                "DATA": {"user_id": user.id, "username": user.username},
            }
        )
        return True

    async def _user_for_token(self, token) -> Optional[User]:
        """Validate *token*, sending ``WS_AUTH_ERROR`` on failure.

        :param token: The JWT access token.
        :returns: The (detached) User, or None if the token is not acceptable.
        """
        jwt_service = self.application.jwt_service
        error = None
        payload = None
        if await jwt_service.is_token_revoked(token):
            error = "Revoked token"
        else:
            payload = jwt_service.decode_access_token(token)
            if not payload or "user_id" not in payload:
                error = "Invalid or expired token"
            elif not jwt_service.validate_token_age(payload):
                error = "Token expired (lifetime exceeded)"
        user = None
        if error is None:
            with self.make_session() as session:
                user = session.get(User, int(payload["user_id"]))
                if user is None:
                    error = "User not found"
                else:
                    session.expunge(user)
        if error is not None:
            await self.write_message({"OP": "WS_AUTH_ERROR", "DATA": error})
            return None
        return user

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

        if ws_op in ("AUTHENTICATE", "REFRESH_TOKEN"):
            await self._handle_auth_op(ws_op, message)
        elif ws_op in self._SCRIPT_ROOM_OP_HANDLERS:
            await self._handle_script_room_op(ws_op, message)
        else:
            await self._handle_session_op(ws_op, message)

    async def _handle_auth_op(self, ws_op: str, message: dict) -> None:
        """Handle ``AUTHENTICATE`` / ``REFRESH_TOKEN``.

        :param ws_op: The operation code.
        :param message: The full parsed message dict.
        """
        token = message.get("DATA", {}).get("token")
        if not token:
            await self.write_message(
                {"OP": "WS_AUTH_ERROR", "DATA": "No token provided"}
            )
            return
        success = await self.authenticate_with_token(token)
        if success and ws_op == "REFRESH_TOKEN":
            await self.write_message({"OP": "WS_TOKEN_REFRESH_SUCCESS", "DATA": {}})

    async def _handle_session_op(self, ws_op: str, message: dict) -> None:
        """Handle client-session and live-show operations.

        :param ws_op: The operation code.
        :param message: The full parsed message dict.
        """
        with self.make_session() as session:
            entry: Session = session.get(Session, self.__getattribute__("internal_id"))
            current_show = await self.application.digi_settings.get("current_show")
            show = session.get(Show, current_show) if current_show else None

            if ws_op == "NEW_CLIENT":
                await self._claim_vacant_leadership(session, show)
            elif ws_op == "REFRESH_CLIENT":
                self._resume_client(message.get("DATA"))
            elif ws_op in self._LEADER_OP_HANDLERS:
                show_session = (
                    session.get(ShowSession, show.current_session_id)
                    if show and show.current_session_id
                    else None
                )
                # Ownership rule: only the authenticated show user on its own row.
                if self._is_leader(session, show_session):
                    handler = getattr(self, self._LEADER_OP_HANDLERS[ws_op])
                    await handler(session, show_session, entry, message["DATA"])
            elif ws_op == "LIVE_SHOW_JUMP_TO_PAGE":
                await self._jump_to_page(session, show, message["DATA"])
            else:
                get_logger().warning(
                    f"Unknown OP {ws_op} received from "
                    f"WebSocket connection {self.request.remote_ip}"
                )

    def _resume_client(self, new_uuid: Any) -> None:
        """Handle ``REFRESH_CLIENT``: a reconnecting page resumes its old uuid.

        This restores *identity only*. It deletes the placeholder row that
        :meth:`open` created and switches this connection to *new_uuid*, taking
        over that uuid's Session row if it still exists; otherwise a new row
        with no edit/cut flags is created. It does **not** cancel the uuid's
        grace deadline and grants nothing: uuids are not secret, so the lock and
        leadership recorded against the uuid can only be used once this
        connection authenticates as the row's owner (see :meth:`_owned_row`), and
        only that authentication cancels the deadline
        (:meth:`_reconcile_after_auth`). A connection can resume at most once,
        and invalid payloads are ignored.

        :param new_uuid: The uuid the client asks to resume.
        """
        if not isinstance(new_uuid, str) or not new_uuid:
            get_logger().warning(
                f"REFRESH_CLIENT with invalid uuid from {self.request.remote_ip}"
            )
            return
        if self._resumed:
            get_logger().warning(
                f"Ignoring repeated REFRESH_CLIENT from {self.request.remote_ip}; "
                f"this connection already resumed a client"
            )
            return
        if new_uuid == self.__getattribute__("internal_id"):
            return

        with self.make_session() as session:
            placeholder = session.get(Session, self._placeholder_id)
            if placeholder is not None:
                session.delete(placeholder)
                session.flush()
            entry = session.get(Session, new_uuid)
            if entry is None:
                session.add(
                    Session(
                        internal_id=new_uuid,
                        remote_ip=self.request.remote_ip,
                        last_ping=self._last_ping,
                        last_pong=self._last_pong,
                    )
                )
            else:
                entry.remote_ip = self.request.remote_ip
                entry.last_ping = self._last_ping
                entry.last_pong = self._last_pong
            session.commit()
        # Only switch in memory once the database agrees.
        self.__setattr__("internal_id", new_uuid)
        self._resumed = True
        get_logger().info(
            f"WebSocket from {self.request.remote_ip} resumed client {new_uuid}"
        )

        if self.current_user_id is not None:
            # Already authenticated on this socket: settle ownership now.
            self._reconcile_after_auth(self.current_user_id)

    async def _op_script_scroll(self, session, show_session, entry, data) -> None:
        """Leader op ``SCRIPT_SCROLL``: record and broadcast the leader's line."""
        show_session.latest_line_ref = data["current_line"]
        session.commit()
        await self.application.ws_send_to_all("NOOP", "SCRIPT_SCROLL", data)

    async def _op_begin_interval(self, session, show_session, entry, data) -> None:
        """Leader op ``BEGIN_INTERVAL``: start an interval after the given act."""
        act: Act = session.get(Act, data["actId"])
        if not entry:
            return
        show_interval = Interval(
            session_id=show_session.id,
            act_id=act.id,
            initial_length=data["length"],
        )
        session.add(show_interval)
        session.flush()
        show_session.current_interval_id = show_interval.id
        session.commit()
        await self.application.ws_send_to_all("NOOP", "GET_SHOW_SESSION_DATA", {})

    async def _op_end_interval(self, session, show_session, entry, data) -> None:
        """Leader op ``END_INTERVAL``: end the current interval."""
        current_interval: Interval = session.get(
            Interval, show_session.current_interval_id
        )
        if current_interval:
            current_interval.end_datetime = datetime.datetime.now(
                tz=datetime.timezone.utc
            )
        show_session.current_interval_id = None
        session.commit()
        await self.application.ws_send_to_all("NOOP", "GET_SHOW_SESSION_DATA", {})

    async def _op_reload_clients(self, session, show_session, entry, data) -> None:
        """Leader op ``RELOAD_CLIENTS``: tell every client to reload."""
        await self.application.ws_send_to_all("RELOAD_CLIENT", "NOOP", {})

    async def _jump_to_page(self, session, show: Optional[Show], data) -> None:
        """Handle ``LIVE_SHOW_JUMP_TO_PAGE``: move the live position and reload all.

        Not leader-gated (unchanged from before this PR).
        """
        if not (show and show.current_session_id):
            return
        show_session = session.get(ShowSession, show.current_session_id)
        if show_session:
            show_session.latest_line_ref = f"page_{data['page']}_line_0"
            session.commit()
            await self.application.ws_send_to_all("RELOAD_CLIENT", "NOOP", {})

    async def _claim_vacant_leadership(self, session, show: Optional[Show]) -> None:
        """Handle ``NEW_CLIENT``: take live-show leadership if nobody holds it.

        Only a connection authenticated as the show session's user, on a row it
        owns, can claim it.

        :param session: Active SQLAlchemy session.
        :param show: The currently loaded Show, or None.
        """
        if not (self.current_user_id and show and show.current_session_id):
            return
        show_session = session.get(ShowSession, show.current_session_id)
        if (
            show_session is None
            or show_session.client_internal_id
            or show_session.user_id != self.current_user_id
            or self._owned_row(session) is None
        ):
            return
        show_session.client_internal_id = self.__getattribute__("internal_id")
        # A fresh leader supersedes any earlier leader's claim to reclaim on
        # reconnect (same as election does).
        show_session.last_client_internal_id = None
        session.commit()
        await self.write_message(
            {
                "OP": "NOOP",
                "ACTION": "ELECTED_LEADER",
                "DATA": {"latest_line_ref": show_session.latest_line_ref},
            }
        )
        await self.application.ws_send_to_all("NOOP", "GET_SHOW_SESSION_DATA", {})

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
        if entry is None or not entry.is_editor or self._owned_row(session) is None:
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

        handler = getattr(self, self._SCRIPT_ROOM_OP_HANDLERS[ws_op])
        await handler(room_manager, data)

    async def _op_request_script_edit(self, room_manager, data: dict) -> None:
        """Handle ``REQUEST_SCRIPT_EDIT`` (see :meth:`_handle_script_room_op`)."""
        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__("internal_id"))
            if entry is None:
                get_logger().warning(
                    "REQUEST_SCRIPT_EDIT: session entry not found (race with on_close?)"
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

            # Ownership rule: the lock is recorded against this uuid's row,
            # so only a connection authenticated as the row's owner may take it.
            if (
                not self._user_has_script_write_access(session, show)
                or self._owned_row(session) is None
            ):
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

            cutters = session.scalars(select(Session).where(Session.is_cutting)).all()
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

        await self.application.ws_send_to_all("NOOP", "GET_SCRIPT_CONFIG_STATUS", {})

    async def _op_request_script_cuts(self, room_manager, data: dict) -> None:
        """Handle ``REQUEST_SCRIPT_CUTS`` (see :meth:`_handle_script_room_op`)."""
        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__("internal_id"))
            if entry is None:
                get_logger().warning(
                    "REQUEST_SCRIPT_CUTS: session entry not found (race with on_close?)"
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

            # Ownership rule: the lock is recorded against this uuid's row,
            # so only a connection authenticated as the row's owner may take it.
            if (
                not self._user_has_script_write_access(session, show)
                or self._owned_row(session) is None
            ):
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

            editors = session.scalars(select(Session).where(Session.is_editor)).all()
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
                script = session.scalar(select(Script).where(Script.show_id == show.id))
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

        await self.application.ws_send_to_all("NOOP", "GET_SCRIPT_CONFIG_STATUS", {})

    async def _op_stop_script_edit(self, room_manager, data: dict) -> None:
        """Handle ``STOP_SCRIPT_EDIT`` (see :meth:`_handle_script_room_op`)."""
        with self.make_session() as session:
            # Only the owner can give up the lock; a socket that merely
            # presented the uuid must not be able to strip it.
            entry = self._owned_row(session)
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

        await self.application.ws_send_to_all("NOOP", "GET_SCRIPT_CONFIG_STATUS", {})

    async def _op_join_script_room(self, room_manager, data: dict) -> None:
        """Handle ``JOIN_SCRIPT_ROOM`` (see :meth:`_handle_script_room_op`)."""
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
                ws_session = self._owned_row(role_session)
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
        await self.application.ws_send_to_all("NOOP", "GET_SCRIPT_CONFIG_STATUS", {})

    async def _op_leave_script_room(self, room_manager, data: dict) -> None:
        """Handle ``LEAVE_SCRIPT_ROOM`` (see :meth:`_handle_script_room_op`)."""
        room = room_manager.get_room_for_client(self)
        if room:
            room.remove_client(self)
            # Broadcast updated member list to remaining clients
            with self.make_session() as session:
                await room.broadcast_members(session)
            await self.application.ws_send_to_all(
                "NOOP", "GET_SCRIPT_CONFIG_STATUS", {}
            )

    async def _op_yjs_sync(self, room_manager, data: dict) -> None:
        """Handle ``YJS_SYNC`` (see :meth:`_handle_script_room_op`)."""
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

    async def _op_yjs_update(self, room_manager, data: dict) -> None:
        """Handle ``YJS_UPDATE`` (see :meth:`_handle_script_room_op`)."""
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

    async def _op_yjs_awareness(self, room_manager, data: dict) -> None:
        """Handle ``YJS_AWARENESS`` (see :meth:`_handle_script_room_op`)."""
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

    async def _op_save_script_draft(self, room_manager, data: dict) -> None:
        """Handle ``SAVE_SCRIPT_DRAFT`` (see :meth:`_handle_script_room_op`)."""
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

    async def _op_discard_script_draft(self, room_manager, data: dict) -> None:
        """Handle ``DISCARD_SCRIPT_DRAFT`` (see :meth:`_handle_script_room_op`)."""
        # Not blocked by a live session: discarding is the only recovery path if a
        # live session starts while a draft is open, so it must stay reachable.
        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__("internal_id"))
            if not await self._require_editor_write_access(session, entry):
                return
        await room_manager.discard_room(self)
        await self.application.ws_send_to_all("NOOP", "GET_SCRIPT_CONFIG_STATUS", {})
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
