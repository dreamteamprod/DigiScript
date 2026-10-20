from __future__ import annotations

from copy import deepcopy
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
from utils.web.log_redaction import apply_path_redactions, redact_sensitive_keys
from utils.web.security_headers import apply_security_headers


if TYPE_CHECKING:
    from digi_server.app_server import DigiScriptServer

# Returned by BaseAPIController._loggable_body when a body is not valid JSON.
_NON_JSON = object()


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

    def set_default_headers(self) -> None:
        """Add the baseline security headers to every response."""
        apply_security_headers(self)

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
                    if not self.application.jwt_service.validate_token_age(payload):
                        raise HTTPError(
                            401,
                            log_message="JWT token age exceeded configured lifetime",
                        )
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

    def _redaction_enabled(self) -> bool:
        """Return True if the ``log_redaction`` setting is on."""
        return bool(
            self.application.digi_settings.settings["log_redaction"].get_value()
        )

    def _loggable_raw_body(self) -> Any:
        """Return a non-JSON request body in the form allowed by ``log_redaction``.

        With redaction on only its size is returned, as it cannot be redacted by key.
        """
        if self._redaction_enabled():
            return f"<non-JSON body, {len(self.request.body)} bytes>"
        return self.request.body

    def _loggable_body(self, redacted_data_paths) -> Any:
        """Decode the JSON request body, redacted if ``log_redaction`` is on.

        :param redacted_data_paths: Decorator-supplied patch of paths to redact,
            or None.
        :returns: The body, or the ``_NON_JSON`` sentinel if it is not valid JSON.
        """
        try:
            body = escape.json_decode(self.request.body)
        except BaseException:
            return _NON_JSON
        if self._redaction_enabled():
            body = deepcopy(body)
            body = redact_sensitive_keys(body)
            if redacted_data_paths:
                apply_path_redactions(redacted_data_paths, body)
        return body

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
            logged = self._loggable_body(redacted_data_paths)
            if logged is _NON_JSON:
                log_method = get_logger().debug
                logged = self._loggable_raw_body()
            log_method(
                f"{self.request.method} {self.request.path} {logged}{user_suffix}",
                extra=self._log_extra(),
            )

        super().on_finish()
