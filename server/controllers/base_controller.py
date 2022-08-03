from typing import Optional, Awaitable

from tornado.web import RequestHandler
from tornado_sqlalchemy import SessionMixin


class BaseController(SessionMixin, RequestHandler):
    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(
            f'Data streaming not supported for {self.__class__}')


class BaseAPIController(BaseController):

    def _unimplemented_method(self, *args: str, **kwargs: str) -> None:
        self.set_status(405)
        self.write({'message': '405 not allowed'})
