from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Awaitable, Optional

from tornado import escape, httputil
from tornado.web import HTTPError, RequestHandler

from digi_server.logger import get_logger
from models.models import db
from models.show import Show
from models.user import User
from rbac.role import Role
from schemas.schemas import ShowSchema, UserSchema
from utils.web.jwt_service import (
    TOKEN_EXPIRED,
    TOKEN_REVOKED,
    TOKEN_SESSION_EXPIRED,
    TOKEN_VERSION_INVALID,
    JWTService,
)


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
        self.token_payload: Optional[dict] = None

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
                (
                    payload,
                    reason,
                ) = await self.application.jwt_service.validate_access_token(token)
                if reason == TOKEN_REVOKED:
                    raise HTTPError(401, log_message="JWT revoked")
                if reason in (TOKEN_EXPIRED, TOKEN_SESSION_EXPIRED):
                    raise HTTPError(
                        401, log_message="JWT token age exceeded configured lifetime"
                    )
                if reason == TOKEN_VERSION_INVALID:
                    raise HTTPError(401, log_message="JWT token version invalid")
                if payload:
                    self.token_payload = payload
                    user = session.get(User, int(payload["user_id"]))
                    if user:
                        self.current_user = user_schema.dump(user)

            # If not authenticated via JWT, try API key authentication
            if not self.current_user:
                api_key = self.request.headers.get("X-API-Key", "")
                if api_key:
                    parsed = JWTService.parse_api_key(api_key)
                    user = session.get(User, parsed[0]) if parsed else None
                    if parsed and JWTService.verify_api_key(user, parsed[1]):
                        self.current_user = user_schema.dump(user)
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

    def data_received(self, chunk: bytes) -> Optional[Awaitable[None]]:
        raise RuntimeError(f"Data streaming not supported for {self.__class__}")


class BaseAPIController(BaseController):
    def _unimplemented_method(self, *args: str, **kwargs: str) -> None:
        self.set_status(405)
        self.write({"message": "405 not allowed"})

    def _log_extra(self) -> dict:
        extra: dict = {"remote_ip": self.request.remote_ip}
        if self.current_user:
            extra["username"] = self.current_user.get("username")
            extra["user_id"] = self.current_user.get("id")
        return extra

    def on_finish(self):
        from utils.web.route import Route  # noqa: PLC0415

        if self.request.path in Route.ignored_logging_routes():
            log_method = get_logger().trace
        else:
            log_method = get_logger().debug

        if self.request.body:
            username = self.current_user.get("username") if self.current_user else None
            user_suffix = f" [{username}]" if username else ""

            method_name = self.request.method.lower()
            handler_method = getattr(self, method_name, None)
            redacted_data_paths = getattr(handler_method, "_redacted_data_paths", None)
            try:
                body = escape.json_decode(self.request.body)
            except BaseException:
                get_logger().debug(
                    f"{self.request.method} {self.request.path} {self.request.body}{user_suffix}",
                    extra=self._log_extra(),
                )
            else:
                if (
                    redacted_data_paths
                    and self.application.digi_settings.settings[
                        "log_redaction"
                    ].get_value()
                ):
                    body = deepcopy(body)
                    redacted_data_paths.apply(body)

                log_method(
                    f"{self.request.method} {self.request.path} {body}{user_suffix}",
                    extra=self._log_extra(),
                )

        super().on_finish()
