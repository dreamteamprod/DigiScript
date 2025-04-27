import functools
from typing import Awaitable, Callable, Optional

from tornado.web import HTTPError

from utils.web.base_controller import BaseController


def requires_show(
    method: Callable[..., Optional[Awaitable[None]]],
) -> Callable[..., Optional[Awaitable[None]]]:
    @functools.wraps(method)
    def wrapper(self: BaseController, *args, **kwargs):
        if not self.get_current_show():
            raise HTTPError(400, log_message="No show loaded")
        return method(self, *args, **kwargs)

    return wrapper


def require_admin(
    method: Callable[..., Optional[Awaitable[None]]],
) -> Callable[..., Optional[Awaitable[None]]]:
    @functools.wraps(method)
    def wrapper(self: BaseController, *args, **kwargs):
        if not self.current_user or not self.current_user["is_admin"]:
            raise HTTPError(401, log_message="Not admin user")
        return method(self, *args, **kwargs)

    return wrapper


def no_live_session(
    method: Callable[..., Optional[Awaitable[None]]],
) -> Callable[..., Optional[Awaitable[None]]]:
    @functools.wraps(method)
    def wrapper(self: BaseController, *args, **kwargs):
        current_show = self.get_current_show()
        if current_show and current_show["current_session_id"]:
            raise HTTPError(409, log_message="Current session in progress")
        return method(self, *args, **kwargs)

    return wrapper


def api_authenticated(
    method: Callable[..., Optional[Awaitable[None]]],
) -> Callable[..., Optional[Awaitable[None]]]:
    @functools.wraps(method)
    def wrapper(self: BaseController, *args, **kwargs) -> Optional[Awaitable[None]]:
        if not self.current_user:
            raise HTTPError(401, log_message="User is not logged in")
        return method(self, *args, **kwargs)

    return wrapper
