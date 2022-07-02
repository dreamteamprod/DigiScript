from typing import Optional, Awaitable

from tornado.web import RequestHandler
from tornado_sqlalchemy import SessionMixin


class BaseController(SessionMixin, RequestHandler):
    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(
            f'Data streaming not supported for {self.__class__}')
