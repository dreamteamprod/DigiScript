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
from utils.web.pending_disconnects import disconnect_key, provisional_key
from utils.web.route import ApiRoute, ApiVersion
from utils.web.ws_session_lifecycle import (
    assign_session_user,
    broadcast,
    elect_live_leader,
    get_live_session,
    release_session_privileges,
    safe_write,
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
    #: Attempts at deleting a disconnected client's row before giving up.
    FINALISE_ATTEMPTS = 3
    #: Delay between those attempts, in seconds.
    FINALISE_RETRY_SECONDS = 1.0

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
        # Edit/cut flags or leadership adopted by REFRESH_CLIENT stay provisional
        # until an AUTHENTICATE for their owner confirms them (see _resume_client).
        self._provisional = False
        self._provisional_owner: Optional[int] = None

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
        handler. The Session row (with its edit/cut flags) and live-show
        leadership are released only after the reconnect grace window, by
        :meth:`_finalise_disconnect`. ``REFRESH_CLIENT`` for the same uuid
        cancels that. The handler leaves any collaborative-editing room
        immediately. If it was the room's last editor,
        :func:`close_room_if_editorless` runs after the window; that timer is not
        cancelled, and it does nothing if an editor has rejoined by then. See
        issue #1419.
        """
        if self._close_handled:
            return
        self._close_handled = True

        if self in self.application.clients:
            self.application.clients.remove(self)

        internal_id = getattr(self, "internal_id", None)
        registry = self.application.pending_disconnects
        if self._provisional:
            # Unconfirmed state stays on the row; the disconnect timer (or a new
            # connection's own provisional check) takes over from here.
            registry.cancel(provisional_key(internal_id))
            self._provisional = False
        self._leave_room()

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

        registry.schedule(disconnect_key(internal_id), self._finalise_disconnect)
        get_logger().info(
            f"WebSocket closed from: {user_part} (client {internal_id} held for "
            f"{registry.grace_seconds:g}s reconnect grace window)"
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

    def _finalise_disconnect(self, attempt: int = 1) -> None:
        """Release a disconnected client's state once its grace window has expired.

        Deletes the ``Session`` row. Only after that commit succeeds does it
        announce a released edit/cut lock (``GET_SCRIPT_CONFIG_STATUS``) and hand
        on leadership. If the commit fails (for example SQLite "database is
        locked"), it retries up to :attr:`FINALISE_ATTEMPTS` times. Does nothing
        if a live connection holds the uuid again.

        :param attempt: 1-based attempt number.
        """
        internal_id = self.__getattribute__("internal_id")
        if self.application.get_ws(internal_id) is not None:
            return

        try:
            with self.make_session() as session:
                entry = session.get(Session, internal_id)
                if entry is None:
                    return
                had_lock = bool(entry.is_editor or entry.is_cutting)
                was_leader = entry.live_session is not None
                session.delete(entry)
                session.commit()
        except Exception:
            get_logger().exception(
                f"Error finalising disconnected session {internal_id} "
                f"(attempt {attempt}/{self.FINALISE_ATTEMPTS})"
            )
            if attempt < self.FINALISE_ATTEMPTS:
                self.application.pending_disconnects.schedule(
                    disconnect_key(internal_id),
                    lambda: self._finalise_disconnect(attempt + 1),
                    delay=self.FINALISE_RETRY_SECONDS,
                )
            return

        if had_lock:
            broadcast(self.application, "GET_SCRIPT_CONFIG_STATUS")
        if was_leader:
            elect_live_leader(self.application, internal_id)

    # ------------------------------------------------------------------
    # Provisional state adopted by REFRESH_CLIENT
    # ------------------------------------------------------------------

    def _begin_provisional(self, owner_id: Optional[int]) -> None:
        """Hold adopted edit/cut flags or leadership until auth confirms the owner.

        :param owner_id: The user who owned the resumed row.
        """
        internal_id = self.__getattribute__("internal_id")
        self._provisional = True
        self._provisional_owner = owner_id
        self.application.pending_disconnects.schedule(
            provisional_key(internal_id), self._expire_provisional
        )

    def _end_provisional(self) -> None:
        """Stop tracking provisional state (it was confirmed or revoked)."""
        if self._provisional:
            self.application.pending_disconnects.cancel(
                provisional_key(self.__getattribute__("internal_id"))
            )
        self._provisional = False
        self._provisional_owner = None

    def _revoke_provisional(self, reason: str) -> None:
        """Release adopted state that authentication did not confirm.

        :param reason: Why, for the log.
        """
        if not self._provisional:
            return
        self._end_provisional()
        release_session_privileges(
            self.application, self.__getattribute__("internal_id"), reason
        )

    def _expire_provisional(self) -> None:
        """Grace-window timer: no AUTHENTICATE confirmed the adopted state in time."""
        self._revoke_provisional("not confirmed by authentication in time")

    def _reconcile_after_auth(self, user_id: int) -> None:
        """Bring the row's privileges in line with the user who just authenticated.

        * Adopted (provisional) flags are kept only if *user_id* owned the row.
        * Flags on a row owned by someone else (or by nobody) are released.
        * Leadership is kept only if *user_id* is the show session's user.
        * The departed leader coming back later (after its window expired, with
          nobody else leading) reclaims leadership here: only for the uuid named
          in ``last_client_internal_id`` and only for the show session's user.

        :param user_id: The authenticated user.
        """
        internal_id = self.__getattribute__("internal_id")
        owner_mismatch = self._provisional and self._provisional_owner != user_id
        self._end_provisional()
        with self.make_session() as session:
            entry = session.get(Session, internal_id)
            live_session = get_live_session(self.application, session)
            if entry is not None and entry.user_id != user_id:
                owner_mismatch = owner_mismatch or bool(
                    entry.is_editor or entry.is_cutting
                )
            leader_mismatch = (
                live_session is not None
                and live_session.client_internal_id == internal_id
                and live_session.user_id != user_id
            )
        if owner_mismatch or leader_mismatch:
            release_session_privileges(
                self.application,
                internal_id,
                "authenticated as a different user",
                flags=owner_mismatch,
                leadership=leader_mismatch,
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

    def _is_leader(self, show_session: Optional[ShowSession]) -> bool:
        """Return True if this connection may act as the live-show leader.

        Leadership adopted by REFRESH_CLIENT counts only once auth confirms it.

        :param show_session: The running show session, or None.
        """
        return (
            show_session is not None
            and not self._provisional
            and show_session.client_internal_id == self.__getattribute__("internal_id")
        )

    async def authenticate_with_token(self, token):
        """Authenticate using a JWT token.

        On failure, any state this connection adopted through REFRESH_CLIENT and
        has not had confirmed is released straight away.

        :param token: The JWT access token.
        :returns: True on success.
        """
        user = await self._user_for_token(token)
        if user is None:
            self._revoke_provisional("authentication failed")
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

        # Handle JWT authentication operations
        if ws_op == "AUTHENTICATE":
            token = message.get("DATA", {}).get("token")
            if token:
                await self.authenticate_with_token(token)
            else:
                self._revoke_provisional("AUTHENTICATE without a token")
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
                self._resume_client(message.get("DATA"))
            elif ws_op == "SCRIPT_SCROLL":
                if show and show.current_session_id:
                    show_session = session.get(ShowSession, show.current_session_id)
                    if self._is_leader(show_session):
                        show_session.latest_line_ref = message["DATA"]["current_line"]
                        session.commit()
                        await self.application.ws_send_to_all(
                            "NOOP", "SCRIPT_SCROLL", message["DATA"]
                        )
            elif ws_op == "BEGIN_INTERVAL":
                if show and show.current_session_id:
                    show_session = session.get(ShowSession, show.current_session_id)
                    if self._is_leader(show_session):
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
                    if self._is_leader(show_session):
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
                    if self._is_leader(show_session):
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

    def _resume_client(self, new_uuid: Any) -> None:
        """Handle ``REFRESH_CLIENT``: a reconnecting page resumes its old uuid.

        Cancels the old uuid's pending disconnect finalisation, deletes the
        placeholder row that :meth:`open` created for this connection, and takes
        over the old uuid's Session row if it still exists (that is, inside the
        grace window). Otherwise a new row with no edit/cut flags is created.
        A connection can resume at most once, and invalid payloads are ignored.

        Adopted edit/cut flags, and leadership if the uuid still leads the live
        show, are *provisional*: the adopting connection has not proved who it is
        yet (client-v3 sends REFRESH_CLIENT before AUTHENTICATE, and uuids are not
        secret). They are confirmed only by an AUTHENTICATE as the row's owner
        (and, for leadership, the show session's user). A failed or mismatched
        AUTHENTICATE releases them at once, and so does the grace window
        expiring without one (:meth:`_expire_provisional`). Leadership that has
        already been released is reclaimed on AUTHENTICATE, never here (see
        :meth:`_reclaim_leadership`).

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
        self._resumed = True

        was_pending = self.application.pending_disconnects.cancel(
            disconnect_key(new_uuid)
        )
        privileged = False
        owner_id = None
        with self.make_session() as session:
            placeholder = session.get(Session, self._placeholder_id)
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
                owner_id = entry.user_id
                live_session = get_live_session(self.application, session)
                privileged = bool(entry.is_editor or entry.is_cutting) or (
                    live_session is not None
                    and live_session.client_internal_id == new_uuid
                )
            session.commit()
        get_logger().info(
            f"WebSocket from {self.request.remote_ip} resumed client {new_uuid} "
            f"({'within grace window' if was_pending else 'no pending disconnect'}"
            f"{', session state held provisionally' if privileged else ''})"
        )

        if not privileged:
            return
        self._begin_provisional(owner_id)
        if self.current_user_id is not None:
            # Already authenticated on this socket: confirm or revoke now.
            self._reconcile_after_auth(self.current_user_id)
        elif owner_id is None:
            self._revoke_provisional("resumed state has no owner to confirm it")

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
