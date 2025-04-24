from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Optional

from tornado import escape, httputil
from tornado.web import HTTPError, RequestHandler
from tornado_sqlalchemy import SessionMixin

from digi_server.logger import get_logger
from models.models import db
from models.show import Show
from models.user import User
from rbac.role import Role
from schemas.schemas import ShowSchema, UserSchema
from utils.web.jwt_utils import decode_access_token, get_token_from_authorization_header

if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


class BaseController(SessionMixin, RequestHandler):

    def __init__(
        self,
        application: DigiScriptServer,
        request: httputil.HTTPServerRequest,
        **kwargs: Any,
    ) -> None:
        super().__init__(application, request, **kwargs)
        self.application: DigiScriptServer = self.application
        self.current_show: Optional[dict] = None

    # pylint: disable=invalid-overridden-method
    async def prepare(
        self,
    ) -> Optional[Awaitable[None]]:
        show_schema = ShowSchema()
        user_schema = UserSchema()

        # Extract JWT token from header
        auth_header = self.request.headers.get("Authorization", "")
        token = get_token_from_authorization_header(auth_header)

        with self.make_session() as session:
            # If we have a token, try to authenticate with it
            if token:
                payload = decode_access_token(token)
                if payload and "user_id" in payload:
                    user = session.query(User).get(int(payload["user_id"]))
                    if user:
                        self.current_user = user_schema.dump(user)

            # Fallback to cookie authentication (backwards compatability, for now)
            if not self.current_user:
                user_id = self.get_secure_cookie("digiscript_user_id")
                if user_id:
                    user = session.query(User).get(int(user_id))
                    if user:
                        self.current_user = user_schema.dump(user)
                    else:
                        self.clear_cookie("digiscript_user_id")

            current_show = await self.application.digi_settings.get("current_show")
            if current_show:
                show = session.query(Show).get(current_show)
                if show:
                    self.current_show = show_schema.dump(show)
        return

    def requires_role(self, resource: db.Model, role: Role):
        if not self.current_user:
            raise HTTPError(401, log_message="Not logged in")
        if self.current_user["is_admin"]:
            return
        with self.make_session() as session:
            user = session.query(User).get(self.current_user["id"])
            if not user:
                raise HTTPError(500)
            if not self.application.rbac.has_role(user, resource, role):
                raise HTTPError(403, log_message="Not authorised")

    def get_current_show(self) -> Optional[dict]:
        return self.current_show

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(f"Data streaming not supported for {self.__class__}")


class BaseAPIController(BaseController):

    def _unimplemented_method(self, *args: str, **kwargs: str) -> None:
        self.set_status(405)
        self.write({"message": "405 not allowed"})

    def on_finish(self):
        if self.request.body:
            try:
                get_logger().debug(
                    f"{self.request.method} "
                    f"{self.request.path} "
                    f"{escape.json_decode(self.request.body)}"
                )
            except BaseException:
                get_logger().debug(
                    f"{self.request.method} "
                    f"{self.request.path} "
                    f"{self.request.body}"
                )
        super().on_finish()
