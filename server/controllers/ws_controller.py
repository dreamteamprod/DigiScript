import json
from typing import Optional, Awaitable, Union

from uuid import uuid4
from tornado import gen
from tornado.websocket import WebSocketHandler
from tornado_sqlalchemy import SessionMixin

from utils.logger import get_logger
from models.models import Session
from utils.route import ApiRoute, ApiVersion


@ApiRoute('ws', ApiVersion.v1)
class WebSocketController(SessionMixin, WebSocketHandler):

    def update_session(self):
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

    def on_close(self) -> None:
        if self in self.application.clients:
            self.application.clients.remove(self)

        with self.make_session() as session:
            entry = session.get(Session, self.__getattribute__('internal_id'))
            if entry:
                session.delete(entry)
                session.commit()

        get_logger().info(f'WebSocket closed from: {self.request.remote_ip}')

    def on_message(self, message: Union[str, bytes]
                   ) -> Optional[Awaitable[None]]:
        get_logger().debug(
            f'WebSocket received data from {self.request.remote_ip}: {message}')

        message = json.loads(message)
        ws_op = message['OP']
        if ws_op == 'SET_UUID':
            with self.make_session() as session:
                entry = session.get(Session, self.__getattribute__('internal_id'))
                if entry:
                    session.delete(entry)
                    session.commit()
            self.__setattr__('internal_id', message['DATA'])
            self.update_session()
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
