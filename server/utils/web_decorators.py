import functools
from typing import Callable, Optional, Awaitable

from tornado.web import HTTPError

from utils.base_controller import BaseController


def requires_show(
        method: Callable[..., Optional[Awaitable[None]]]
) -> Callable[..., Optional[Awaitable[None]]]:
    @functools.wraps(method)
    def wrapper(self: BaseController, *args, **kwargs):
        if not self.get_current_show():
            raise HTTPError(400, log_message='No show loaded')

        return method(self, *args, **kwargs)

    return wrapper


def no_live_session(
        method: Callable[..., Optional[Awaitable[None]]]
) -> Callable[..., Optional[Awaitable[None]]]:
    @functools.wraps(method)
    def wrapper(self: BaseController, *args, **kwargs):
        current_show = self.get_current_show()
        if current_show and current_show['current_session_id']:
            raise HTTPError(409, log_message='Current session in progress')

        return method(self, *args, **kwargs)

    return wrapper
