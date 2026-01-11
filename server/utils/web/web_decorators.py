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


def allow_when_password_required(
    method: Callable[..., Optional[Awaitable[None]]],
) -> Callable[..., Optional[Awaitable[None]]]:
    """
    Decorator to mark a handler method as accessible even when user has requires_password_change=True.

    Apply this to specific HTTP methods (get, post, patch, etc.) that should be accessible
    during forced password change, such as change-password and logout endpoints.

    Example:
        @allow_when_password_required
        async def patch(self):
            # Password change logic
    """

    @functools.wraps(method)
    def wrapper(self: BaseController, *args, **kwargs) -> Optional[Awaitable[None]]:
        return method(self, *args, **kwargs)

    # Mark the wrapper with an attribute so prepare() can detect it
    wrapper._allow_when_password_required = True  # type: ignore
    return wrapper
