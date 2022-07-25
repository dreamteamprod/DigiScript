from typing import Optional, Awaitable

from tornado.web import RequestHandler
from tornado_sqlalchemy import SessionMixin


class BaseController(SessionMixin, RequestHandler):
    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(
            f'Data streaming not supported for {self.__class__}')


class BaseAPIController(BaseController):
    def get(self):
        self.set_status(501)
        self.write({'message': '501 not implemented'})

    def post(self):
        self.set_status(501)
        self.write({'message': '501 not implemented'})

    def patch(self):
        self.set_status(501)
        self.write({'message': '501 not implemented'})

    def delete(self):
        self.set_status(501)
        self.write({'message': '501 not implemented'})
