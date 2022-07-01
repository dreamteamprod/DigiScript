from tornado.web import RequestHandler
from tornado.websocket import WebSocketHandler
from tornado_sqlalchemy import SessionMixin, as_future
from typing import Optional, Awaitable, Union

from logger import get_logger
from models import Session
from route import ApiRoute, ApiVersion, Route


class BaseController(SessionMixin, RequestHandler):
    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(f'Data streaming not supported for {self.__class__}')


@Route('/debug')
class DebugController(BaseController):
    def get(self):
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        self.write({'status': 'OK'})


@ApiRoute('debug', ApiVersion.v1)
class ApiDebugController(BaseController):
    def get(self):
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        self.write({'status': 'OK', 'api_version': 1})


@ApiRoute('ws', ApiVersion.v1)
class WebSocketController(SessionMixin, WebSocketHandler):

    clients = []

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(f'Data streaming not supported for {self.__class__}')

    def check_origin(self, origin):
        if self.settings.get('debug', False):
            return True
        return super().check_origin(origin)

    def open(self, *args: str, **kwargs: str) -> Optional[Awaitable[None]]:
        self.clients.append(self)

        # TODO: This assumes only one session from a single client IP, which might not be true
        with self.make_session() as session:
            session.add(Session(remote_ip=self.request.remote_ip,
                                last_ping=self.ws_connection.last_ping,
                                last_pong=self.ws_connection.last_pong))
            session.commit()

        get_logger().info(f'WebSocket opened from: {self.request.remote_ip}')

    def on_close(self) -> None:
        if self in self.clients:
            self.clients.remove(self)

        # TODO: This assumes only one session from a single client IP, which might not be true
        with self.make_session() as session:
            entry = session.get(Session, self.request.remote_ip)
            session.delete(entry)
            session.commit()

        get_logger().info(f'WebSocket closed from: {self.request.remote_ip}')

    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        pass

    def update_session(self):
        with self.make_session() as session:
            entry = session.get(Session, self.request.remote_ip)
            entry.last_ping = self.ws_connection.last_ping
            entry.last_pong = self.ws_connection.last_pong
            session.commit()

    def on_pong(self, data: bytes) -> None:
        self.update_session()
        get_logger().trace(f'Ping response from {self.request.remote_ip} : {data.hex()}')

    def on_ping(self, data: bytes) -> None:
        self.update_session()
        get_logger().trace(f'Ping from {self.request.remote_ip} : {data.hex()}')
