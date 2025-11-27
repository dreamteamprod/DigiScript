from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Optional

import bcrypt
from tornado import escape, httputil
from tornado.ioloop import IOLoop
from tornado.web import HTTPError, RequestHandler
from tornado_sqlalchemy import SessionMixin

from digi_server.logger import get_logger
from models.models import db
from models.show import Show
from models.user import User
from rbac.role import Role
from schemas.schemas import ShowSchema, UserSchema

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

        with self.make_session() as session:
            # First, try JWT authentication
            auth_header = self.request.headers.get("Authorization", "")
            token = self.application.jwt_service.get_token_from_authorization_header(
                auth_header
            )

            if token:
                is_revoked = await self.application.jwt_service.is_token_revoked(token)
                if is_revoked:
                    raise HTTPError(401, log_message="JWT revoked")

                payload = self.application.jwt_service.decode_access_token(token)
                if payload and "user_id" in payload:
                    user = session.query(User).get(int(payload["user_id"]))
                    if user:
                        self.current_user = user_schema.dump(user)

            # If not authenticated via JWT, try API token authentication
            if not self.current_user:
                api_key = self.request.headers.get("X-API-Key", "")
                if api_key:
                    # Get all users with API tokens and check each one
                    users_with_tokens = (
                        session.query(User).filter(User.api_token.isnot(None)).all()
                    )

                    authenticated_user = None
                    for user in users_with_tokens:
                        # Compare the provided token with the hashed token
                        token_matches = await IOLoop.current().run_in_executor(
                            None,
                            bcrypt.checkpw,
                            escape.utf8(api_key),
                            escape.utf8(user.api_token),
                        )
                        if token_matches:
                            authenticated_user = user
                            break

                    if authenticated_user:
                        self.current_user = user_schema.dump(authenticated_user)
                    else:
                        raise HTTPError(401, log_message="Invalid API key")

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
