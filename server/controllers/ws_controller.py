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

from digi_server.logger import get_logger
from models.session import Interval, Session, ShowSession
from models.show import Act, Show
from models.user import User
from utils.web.base_controller import DatabaseMixin
from utils.web.route import ApiRoute, ApiVersion


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


@ApiRoute("ws", ApiVersion.V1)
class WebSocketController(DatabaseMixin, WebSocketHandler):
    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.application: DigiScriptServer = application
        self.current_user_id = None
        self._last_ping = 0.0
        self._last_pong = 0.0

    def update_session(self, is_editor=False, user_id=None):
        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__("internal_id"))
            if entry:
                entry.last_ping = self._last_ping
                entry.last_pong = self._last_pong
                # Update user_id if it has changed
                if user_id is not None and entry.user_id != user_id:
                    entry.user_id = user_id
            else:
                session.add(
                    Session(
                        internal_id=self.__getattribute__("internal_id"),
                        remote_ip=self.request.remote_ip,
                        last_ping=self._last_ping,
                        last_pong=self._last_pong,
                        user_id=user_id,
                        is_editor=is_editor,
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
        if self in self.application.clients:
            self.application.clients.remove(self)

        # Remove from any collaborative editing room
        if hasattr(self.application, "room_manager") and self.application.room_manager:
            room = self.application.room_manager.get_room_for_client(self)
            if room:
                room.remove_client(self)
                # Schedule async broadcast (on_close is sync, so use add_callback)
                app = self.application

                async def _broadcast():
                    with app.get_db().sessionmaker() as session:
                        await room.broadcast_members(session)

                IOLoop.current().add_callback(_broadcast)

        notify_editor_change = False
        elect_live_leader = False

        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__("internal_id"))
            if entry:
                if entry.is_editor:
                    notify_editor_change = True
                if entry.live_session:
                    elect_live_leader = True

                session.delete(entry)
                session.commit()

        if notify_editor_change:
            for client in self.application.clients:
                client.write_message(
                    {"OP": "NOOP", "ACTION": "GET_SCRIPT_CONFIG_STATUS", "DATA": {}}
                )

        if elect_live_leader:
            current_show = self.application.digi_settings.settings.get(
                "current_show"
            ).get_value()
            if current_show:
                with self.make_session() as session:
                    show = session.get(Show, current_show)
                    if show.current_session_id:
                        live_session: ShowSession = session.get(
                            ShowSession, show.current_session_id
                        )
                        live_session.last_client_internal_id = self.__getattribute__(
                            "internal_id"
                        )
                        session.flush()
                        next_session: Session = session.scalars(
                            select(Session).where(
                                Session.user_id == live_session.user_id
                            )
                        ).first()
                        if next_session:
                            next_ws = self.application.get_ws(next_session.internal_id)
                            if not next_ws:
                                get_logger().error(
                                    "Unable to elect new leader of live session"
                                )
                            else:
                                live_session.client_internal_id = (
                                    next_session.internal_id
                                )
                                live_session.last_client_internal_id = None
                                next_ws.write_message(
                                    {
                                        "OP": "NOOP",
                                        "ACTION": "ELECTED_LEADER",
                                        "DATA": {
                                            "latest_line_ref": live_session.latest_line_ref
                                        },
                                    }
                                )
                        else:
                            for client in self.application.clients:
                                client.write_message(
                                    {"OP": "NOOP", "ACTION": "NO_LEADER", "DATA": {}}
                                )

                        session.commit()
                        for client in self.application.clients:
                            client.write_message(
                                {
                                    "OP": "NOOP",
                                    "ACTION": "GET_SHOW_SESSION_DATA",
                                    "DATA": {},
                                }
                            )

        get_logger().info(f"WebSocket closed from: {self.request.remote_ip}")

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

        with self.make_session() as session:
            user = session.get(User, int(payload["user_id"]))
            if not user:
                await self.write_message(
                    {"OP": "WS_AUTH_ERROR", "DATA": "User not found"}
                )
                return False

            # Update the user ID for this connection
            self.current_user_id = user.id

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
        get_logger().debug(
            f"WebSocket received data from {self.request.remote_ip}: {message}"
        )

        message = json.loads(message)
        ws_op = message["OP"]

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

        # Handle collaborative editing operations (Yjs sync protocol)
        if ws_op in (
            "JOIN_SCRIPT_ROOM",
            "LEAVE_SCRIPT_ROOM",
            "YJS_SYNC",
            "YJS_UPDATE",
            "YJS_AWARENESS",
        ):
            await self._handle_collab_op(ws_op, message)
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
                new_uuid = message["DATA"]
                is_editor = False
                update_session_client = False

                if entry:
                    is_editor = entry.is_editor
                    if show and show.current_session_id:
                        show_session = session.get(ShowSession, show.current_session_id)
                        if (
                            show_session
                            and show_session.last_client_internal_id == new_uuid
                        ):
                            update_session_client = True

                    session.delete(entry)
                    session.commit()

                self.__setattr__("internal_id", new_uuid)
                self.update_session(is_editor=is_editor, user_id=self.current_user_id)
                if update_session_client:
                    show_session.client_internal_id = new_uuid
                    show_session.last_client_internal_id = None
                    session.commit()
                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SHOW_SESSION_DATA", {}
                    )
            elif ws_op == "REQUEST_SCRIPT_EDIT":
                editors = session.scalars(
                    select(Session).where(Session.is_editor)
                ).all()
                if len(editors) == 0:
                    entry.is_editor = True
                    session.commit()
                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SCRIPT_CONFIG_STATUS", {}
                    )
                else:
                    await self.write_message(
                        {"OP": "NOOP", "ACTION": "REQUEST_EDIT_FAILURE", "DATA": {}}
                    )
            elif ws_op == "STOP_SCRIPT_EDIT":
                if entry.is_editor:
                    entry.is_editor = False
                    session.commit()
                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SCRIPT_CONFIG_STATUS", {}
                    )
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

    async def _handle_collab_op(self, ws_op: str, message: dict):
        """Handle collaborative editing WebSocket operations.

        :param ws_op: The operation code.
        :param message: The full parsed message dict.
        """
        room_manager = getattr(self.application, "room_manager", None)
        if not room_manager:
            get_logger().warning("RoomManager not available, ignoring collab OP")
            return

        data = message.get("DATA", {})

        if ws_op == "JOIN_SCRIPT_ROOM":
            revision_id = data.get("revision_id")
            if not revision_id:
                await self.write_message(
                    {"OP": "COLLAB_ERROR", "DATA": {"error": "revision_id required"}}
                )
                return

            role = data.get("role", "editor")
            room = await room_manager.get_or_create_room(revision_id)
            room.add_client(self, role)

            # Send initial sync: full document state
            sync_state = room.get_sync_state()
            await self.write_message(
                {
                    "OP": "YJS_SYNC",
                    "DATA": {
                        "step": 0,
                        "payload": base64.b64encode(sync_state).decode("ascii"),
                        "room_id": f"draft_{revision_id}",
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
                diff = room.get_update_for(decoded)
                await self.write_message(
                    {
                        "OP": "YJS_SYNC",
                        "DATA": {
                            "step": 2,
                            "payload": base64.b64encode(diff).decode("ascii"),
                            "room_id": f"draft_{room.revision_id}",
                        },
                    }
                )
            elif step == 2:
                # Client sends its diff; server applies it
                room.apply_update(decoded)
                await room.broadcast_update(decoded, sender=self)

        elif ws_op == "YJS_UPDATE":
            room = room_manager.get_room_for_client(self)
            if not room:
                return

            payload = data.get("payload", "")
            try:
                decoded = base64.b64decode(payload)
            except Exception:
                get_logger().warning("Invalid base64 in YJS_UPDATE message")
                return

            room.apply_update(decoded)
            await room.broadcast_update(decoded, sender=self)

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
