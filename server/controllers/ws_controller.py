import json
from typing import Optional, Awaitable, Union, TYPE_CHECKING

from uuid import uuid4

from tornado import gen
from tornado.websocket import WebSocketHandler
from tornado_sqlalchemy import SessionMixin

from digi_server.logger import get_logger
from models.session import Session, ShowSession
from models.show import Show
from utils.web.route import ApiRoute, ApiVersion

if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


@ApiRoute('ws', ApiVersion.V1)
class WebSocketController(SessionMixin, WebSocketHandler):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.application: DigiScriptServer = self.application  # pylint: disable=used-before-assignment

    def update_session(self, is_editor=False, user_id=None):
        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__('internal_id'))
            if entry:
                entry.last_ping = self.ws_connection.last_ping
                entry.last_pong = self.ws_connection.last_pong
                session.commit()
            else:
                session.add(Session(internal_id=self.__getattribute__('internal_id'),
                                    remote_ip=self.request.remote_ip,
                                    last_ping=self.ws_connection.last_ping,
                                    last_pong=self.ws_connection.last_pong,
                                    user_id=user_id,
                                    is_editor=is_editor))
                session.commit()

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(
            f'Data streaming not supported for {self.__class__}')

    def check_origin(self, origin):
        if self.settings.get('debug', False):
            return True
        return super().check_origin(origin)

    @gen.coroutine
    def open(self, *args: str, **kwargs: str) -> Optional[Awaitable[None]]:
        self.__setattr__('internal_id', str(uuid4()))
        self.application.clients.append(self)

        user_id = self.get_secure_cookie('digiscript_user_id')
        if user_id is not None:
            user_id = int(user_id)

        self.update_session(user_id=user_id)
        get_logger().info(f'WebSocket opened from: {self.request.remote_ip}')

        yield self.write_message({
            'OP': 'SET_UUID',
            'DATA': self.__getattribute__('internal_id')
        })

        yield self.write_message({
            'OP': 'NOOP',
            'DATA': {},
            'ACTION': 'GET_SETTINGS'
        })

    def on_close(self) -> None:
        if self in self.application.clients:
            self.application.clients.remove(self)

        notify_editor_change = False
        elect_live_leader = False

        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__('internal_id'))
            if entry:
                if entry.is_editor:
                    notify_editor_change = True
                if entry.live_session:
                    elect_live_leader = True

                session.delete(entry)
                session.commit()

        if notify_editor_change:
            for client in self.application.clients:
                client.write_message({
                    'OP': 'NOOP',
                    'ACTION:': 'GET_SCRIPT_CONFIG_STATUS',
                    'DATA': {}
                })

        if elect_live_leader:
            current_show = self.application.digi_settings.settings.get('current_show').get_value()
            if current_show:
                with self.make_session() as session:
                    show = session.query(Show).get(current_show)
                    if show.current_session_id:
                        live_session: ShowSession = session.query(ShowSession).get(show.current_session_id)
                        live_session.last_client_internal_id = self.__getattribute__('internal_id')
                        session.flush()
                        next_session: Session = session.query(Session).filter(Session.user_id == live_session.user_id).first()
                        if next_session:
                            live_session.client_internal_id = next_session.internal_id
                            live_session.last_client_internal_id = None
                            next_ws = self.application.get_ws(next_session.internal_id)
                            if not next_ws:
                                get_logger().error('Unable to elect new leader of live session')
                            else:
                                next_ws.write_message({
                                    'OP': 'NOOP',
                                    'ACTION': 'ELECTED_LEADER',
                                    'DATA': {
                                        'latest_line_ref': live_session.latest_line_ref
                                    }
                                })
                        else:
                            for client in self.application.clients:
                                client.write_message({
                                    'OP': 'NOOP',
                                    'ACTION:': 'NO_LEADER',
                                    'DATA': {}
                                })

                        session.commit()
                        for client in self.application.clients:
                            client.write_message({
                                'OP': 'NOOP',
                                'ACTION': 'GET_SHOW_SESSION_DATA',
                                'DATA': {}
                            })

        get_logger().info(f'WebSocket closed from: {self.request.remote_ip}')

    async def on_message(self, message: Union[str, bytes]): # pylint: disable=invalid-overridden-method
        get_logger().debug(
            f'WebSocket received data from {self.request.remote_ip}: {message}')

        message = json.loads(message)
        ws_op = message['OP']
        with self.make_session() as session:
            entry: Session = session.get(Session, self.__getattribute__('internal_id'))
            current_show = await self.application.digi_settings.get('current_show')
            if current_show:
                show = session.query(Show).get(current_show)
            else:
                show = None
            show_session: Optional[ShowSession] = None

            user_id = self.get_secure_cookie('digiscript_user_id')
            if user_id is not None:
                user_id = int(user_id)

            if ws_op == 'NEW_CLIENT':
                if user_id and show and show.current_session_id:
                    show_session = session.query(ShowSession).get(show.current_session_id)
                    if show_session and not show_session.client_internal_id:
                        if show_session.user_id == user_id:
                            show_session.client_internal_id = self.__getattribute__('internal_id')
                            session.commit()
                            await self.write_message({
                                'OP': 'NOOP',
                                'ACTION': 'ELECTED_LEADER',
                                'DATA': {
                                    'latest_line_ref': show_session.latest_line_ref
                                }
                            })
                            await self.application.ws_send_to_all(
                                'NOOP',
                                'GET_SHOW_SESSION_DATA',
                                {}
                            )
            elif ws_op == 'REFRESH_CLIENT':
                new_uuid = message['DATA']
                is_editor = False
                update_session_client = False

                if entry:
                    is_editor = entry.is_editor
                    if show and show.current_session_id:
                        show_session = session.query(ShowSession).get(show.current_session_id)
                        if show_session and show_session.last_client_internal_id == new_uuid:
                            update_session_client = True

                    session.delete(entry)
                    session.commit()

                self.__setattr__('internal_id', new_uuid)
                self.update_session(is_editor=is_editor, user_id=user_id)
                if update_session_client:
                    show_session.client_internal_id = new_uuid
                    show_session.last_client_internal_id = None
                    session.commit()
                    await self.application.ws_send_to_all(
                        'NOOP',
                        'GET_SHOW_SESSION_DATA',
                        {}
                    )
            elif ws_op == 'REQUEST_SCRIPT_EDIT':
                editors = session.query(Session).filter(Session.is_editor).all()
                if len(editors) == 0:
                    entry.is_editor = True
                    session.commit()
                    await self.application.ws_send_to_all('NOOP', 'GET_SCRIPT_CONFIG_STATUS', {})
                else:
                    await self.write_message({
                        'OP': 'NOOP',
                        'ACTION': 'REQUEST_EDIT_FAILURE',
                        'DATA': {}
                    })
            elif ws_op == 'STOP_SCRIPT_EDIT':
                if entry.is_editor:
                    entry.is_editor = False
                    session.commit()
                    await self.application.ws_send_to_all('NOOP', 'GET_SCRIPT_CONFIG_STATUS', {})
            elif ws_op == 'SCRIPT_SCROLL':
                if show and show.current_session_id:
                    show_session = session.query(ShowSession).get(show.current_session_id)
                    if show_session:
                        if show_session.client_internal_id == self.__getattribute__('internal_id'):
                            show_session.latest_line_ref = message['DATA']['current_line']
                            session.commit()
            else:
                get_logger().warning(f'Unknown OP {ws_op} received from '
                                     f'WebSocket connection {self.request.remote_ip}')

    def on_pong(self, data: bytes) -> None:
        self.update_session()
        get_logger().trace(
            f'Ping response from {self.request.remote_ip} : {data.hex()}')

    def on_ping(self, data: bytes) -> None:
        self.update_session()
        get_logger().trace(
            f'Ping from {self.request.remote_ip} : {data.hex()}')
