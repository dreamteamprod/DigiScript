from typing import Optional, Awaitable, Union

from tornado.websocket import WebSocketHandler
from tornado_sqlalchemy import SessionMixin

from logger import get_logger
from models import Session
from route import ApiRoute, ApiVersion


@ApiRoute('ws', ApiVersion.v1)
class WebSocketController(SessionMixin, WebSocketHandler):

    clients = []

    def update_session(self):
        with self.make_session() as session:
            entry = session.get(Session, self.request.remote_ip)
            if entry:
                entry.last_ping = self.ws_connection.last_ping
                entry.last_pong = self.ws_connection.last_pong
                session.commit()
            else:
                session.add(Session(remote_ip=self.request.remote_ip,
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

    def open(self, *args: str, **kwargs: str) -> Optional[Awaitable[None]]:
        self.clients.append(self)

        # TODO: This assumes only one session from a single client IP, which
        # might not be true
        self.update_session()
        get_logger().info(f'WebSocket opened from: {self.request.remote_ip}')

    def on_close(self) -> None:
        if self in self.clients:
            self.clients.remove(self)

        # TODO: This assumes only one session from a single client IP, which
        # might not be true
        with self.make_session() as session:
            entry = session.get(Session, self.request.remote_ip)
            if entry:
                session.delete(entry)
                session.commit()

        get_logger().info(f'WebSocket closed from: {self.request.remote_ip}')

    def on_message(self, message: Union[str, bytes]
                   ) -> Optional[Awaitable[None]]:
        pass

    def on_pong(self, data: bytes) -> None:
        self.update_session()
        get_logger().trace(
            f'Ping response from {self.request.remote_ip} : {data.hex()}')

    def on_ping(self, data: bytes) -> None:
        self.update_session()
        get_logger().trace(
            f'Ping from {self.request.remote_ip} : {data.hex()}')
