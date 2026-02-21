from __future__ import annotations

from typing import TYPE_CHECKING, Any, Awaitable, Optional

import bcrypt
from sqlalchemy import select
from tornado import escape, httputil
from tornado.ioloop import IOLoop
from tornado.web import HTTPError, RequestHandler

from digi_server.logger import get_logger
from models.models import db
from models.show import Show
from models.user import User
from rbac.role import Role
from schemas.schemas import ShowSchema, UserSchema


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer


class DatabaseMixin:
    """Mixin providing database session management (replaces tornado_sqlalchemy.SessionMixin)."""

    @property
    def db(self):
        """Get database instance from application."""
        return self.application.get_db()

    def make_session(self):
        """Create session context manager."""
        return self.db.sessionmaker()


class BaseController(DatabaseMixin, RequestHandler):
    def __init__(
        self,
        application: DigiScriptServer,
        request: httputil.HTTPServerRequest,
        **kwargs: Any,
    ) -> None:
        super().__init__(application, request, **kwargs)
        self.application: DigiScriptServer = self.application
        self.current_show: Optional[dict] = None

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
                    # Validate token version to check if token is still valid
                    if not self.application.jwt_service.is_token_version_valid(payload):
                        raise HTTPError(401, log_message="JWT token version invalid")

                    user = session.get(User, int(payload["user_id"]))
                    if user:
                        self.current_user = user_schema.dump(user)

            # If not authenticated via JWT, try API token authentication
            if not self.current_user:
                api_key = self.request.headers.get("X-API-Key", "")
                if api_key:
                    # Get all users with API tokens and check each one
                    users_with_tokens = session.scalars(
                        select(User).where(User.api_token.isnot(None))
                    ).all()

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

            # Enforce password change requirement
            if self.current_user and self.current_user.get("requires_password_change"):
                # Check if the current HTTP method is marked as exempt
                method_name = self.request.method.lower()
                handler_method = getattr(self, method_name, None)
                is_exempt = getattr(
                    handler_method, "_allow_when_password_required", False
                )

                if not is_exempt:
                    raise HTTPError(
                        403,
                        log_message="Password change required before accessing this resource",
                    )

            current_show = await self.application.digi_settings.get("current_show")
            if current_show:
                show = session.get(Show, current_show)
                if show:
                    self.current_show = show_schema.dump(show)
        return

    def requires_admin(self):
        if not self.current_user:
            raise HTTPError(401, log_message="Not logged in")
        if not self.current_user["is_admin"]:
            raise HTTPError(403, log_message="Admin access required")

    def requires_role(self, resource: db.Model, role: Role):
        if not self.current_user:
            raise HTTPError(401, log_message="Not logged in")
        if self.current_user["is_admin"]:
            return
        with self.make_session() as session:
            user = session.get(User, self.current_user["id"])
            if not user:
                raise HTTPError(500)
            if not self.application.rbac.has_role(user, resource, role):
                raise HTTPError(403, log_message="Not authorised")

    def get_current_show(self) -> Optional[dict]:
        return self.current_show

    def set_default_headers(self):
        """Set CORS headers to allow requests from Electron app."""
        # Allow all origins (needed for Electron which loads from file://)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header(
            "Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        )
        self.set_header(
            "Access-Control-Allow-Headers",
            "Content-Type, Authorization, X-API-Key, X-Requested-With",
        )
        self.set_header("Access-Control-Max-Age", "3600")

    def options(self, *args):
        """Handle CORS preflight requests."""
        # Just set status 204 No Content for OPTIONS requests
        self.set_status(204)
        self.finish()

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(f"Data streaming not supported for {self.__class__}")


class BaseAPIController(BaseController):
    def _unimplemented_method(self, *args: str, **kwargs: str) -> None:
        self.set_status(405)
        self.write({"message": "405 not allowed"})

    def on_finish(self):
        from utils.web.route import Route  # noqa: PLC0415

        if self.request.path in Route.ignored_logging_routes():
            log_method = get_logger().trace
        else:
            log_method = get_logger().debug

        if self.request.body:
            try:
                log_method(
                    f"{self.request.method} "
                    f"{self.request.path} "
                    f"{escape.json_decode(self.request.body)}"
                )
            except BaseException:
                get_logger().debug(
                    f"{self.request.method} {self.request.path} {self.request.body}"
                )
        super().on_finish()
