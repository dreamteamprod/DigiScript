import json
from typing import Optional, Awaitable, Union, TYPE_CHECKING

from uuid import uuid4

from tornado import gen
from tornado.websocket import WebSocketHandler
from tornado_sqlalchemy import SessionMixin

from digi_server.logger import get_logger
from models.session import Session
from utils.web.route import ApiRoute, ApiVersion

if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


@ApiRoute('ws', ApiVersion.v1)
class WebSocketController(SessionMixin, WebSocketHandler):

    def __init__(self, application, request, **kwargs):
        super().__init__(application, request, **kwargs)
        self.application: DigiScriptServer = self.application  # pylint: disable=used-before-assignment

    def update_session(self, is_editor=None):
        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__('internal_id'))
            if entry:
                entry.last_ping = self.ws_connection.last_ping
                entry.last_pong = self.ws_connection.last_pong
                if is_editor is not None:
                    entry.is_editor = is_editor
                session.commit()
            else:
                session.add(Session(internal_id=self.__getattribute__('internal_id'),
                                    remote_ip=self.request.remote_ip,
                                    last_ping=self.ws_connection.last_ping,
                                    last_pong=self.ws_connection.last_pong))
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

        self.update_session()
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

        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__('internal_id'))
            if entry:
                notify = False
                if entry.is_editor:
                    notify = True

                session.delete(entry)
                session.commit()

                if notify:
                    for client in self.application.clients:
                        client.write_message({
                            'OP': 'NOOP',
                            'ACTION:': 'GET_SCRIPT_CONFIG_STATUS',
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
            if ws_op == 'SET_UUID':
                is_editor = False
                if entry:
                    is_editor = entry.is_editor
                    session.delete(entry)
                    session.commit()
                self.__setattr__('internal_id', message['DATA'])
                self.update_session(is_editor=is_editor)
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
