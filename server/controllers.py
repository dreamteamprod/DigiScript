from tornado.web import RequestHandler
from tornado.websocket import WebSocketHandler
from tornado_sqlalchemy import SessionMixin
from typing import Optional, Awaitable, Union

from logger import get_logger
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

    def open(self, *args, **kwargs):
        get_logger().info(f'WebSocket opened: {repr(self)}')
        self.clients.append(self)

    def on_close(self):
        if self in self.clients:
            self.clients.remove(self)
        get_logger().info(f'WebSocket closed: {repr(self)}')

    def on_message(self, message: Union[str, bytes]) -> Optional[Awaitable[None]]:
        pass
