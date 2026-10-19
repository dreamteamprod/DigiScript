from datetime import datetime, timezone

from sqlalchemy import select
from tornado import escape

from digi_server.logger import get_logger
from models.session import Session
from models.user import User
from registry.named_locks import NamedLockRegistry
from schemas.schemas import UserSchema
from services.password_service import PasswordService
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import (
    allow_when_password_required,
    api_authenticated,
    no_live_session,
    redact_data_paths,
    require_admin,
)
from utils.web.ws_session_lifecycle import (
    assign_session_user,
    holders,
    release_session_privileges,
    row_owner,
    schedule_disconnect_deadline,
)


@ApiRoute("auth/create", ApiVersion.V1)
class UserCreateController(BaseAPIController):
    @redact_data_paths(paths=["/password", "/confirmPassword"])
    async def post(self):
        with self.make_session() as session:
            # If there are no users, allow creation without authentication, otherwise require admin.
            has_any_users = session.scalars(select(User)).first() is not None
            if has_any_users:
                self.requires_admin()

            data = escape.json_decode(self.request.body)

            username = data.get("username", "")
            if not username:
                self.set_status(400)
                await self.finish({"message": "Username missing"})
                return

            password = data.get("password", "")
            if not password:
                self.set_status(400)
                await self.finish({"message": "Password missing"})
                return

            is_admin = data.get("is_admin", False)
            if not has_any_users and not is_admin:
                self.set_status(400)
                await self.finish({"message": "First user must be an admin"})
                return

            # Validate password strength
            is_valid, error_msg = PasswordService.validate_password_strength(password)
            if not is_valid:
                self.set_status(400)
                await self.finish({"message": error_msg})
                return

            async with NamedLockRegistry.acquire(f"UserLock::{username}"):
                conflict_user = session.scalars(
                    select(User).where(User.username == username)
                ).first()
                if conflict_user:
                    self.set_status(400)
                    await self.finish({"message": "Username already taken"})
                    return

                hashed_password = await PasswordService.hash_password(password)

                session.add(
                    User(
                        username=username,
                        password=hashed_password,
                        is_admin=is_admin,
                        created_on=datetime.now(tz=timezone.utc),
                    )
                )
                session.commit()

                if is_admin:
                    await self.application.digi_settings.set("has_admin_user", True)

                self.set_status(200)
                await self.application.ws_send_to_all("NOOP", "GET_USERS", {})
                await self.finish({"message": "Successfully created user"})


@ApiRoute("auth/delete", ApiVersion.V1)
class UserDeleteController(BaseAPIController):
    @api_authenticated
    @require_admin
    @no_live_session
    async def post(self):
        data = escape.json_decode(self.request.body)
        user_to_delete = data.get("id", None)
        if not user_to_delete:
            self.set_status(400)
            await self.finish({"message": "Id missing"})
            return

        with self.make_session() as session:
            user_to_delete: User = session.get(User, int(user_to_delete))
            all_admins = session.scalars(
                select(User).where(User.is_admin.is_(True))
            ).all()
            if not user_to_delete:
                self.set_status(400)
                await self.finish({"message": "Could not find user to delete"})
                return

            if user_to_delete.id == self.current_user["id"]:
                self.set_status(400)
                await self.finish(
                    {"message": "Cannot delete currently authenticated user"}
                )
                return

            if user_to_delete.is_admin and len(all_admins) <= 1:
                self.set_status(400)
                await self.finish({"message": "Cannot delete the only admin user"})
                return

            async with NamedLockRegistry.acquire(
                f"UserLock::{user_to_delete.username}"
            ):
                # Force logout all sessions using UserService
                await self.application.user_service.force_logout_all_sessions(
                    session, user_to_delete
                )

                # Delete all RBAC associations for this user
                self.application.rbac.delete_actor(user_to_delete)

                # Then we can delete the user
                session.delete(user_to_delete)
                session.commit()

                self.set_status(200)
                await self.application.ws_send_to_all("NOOP", "GET_USERS", {})
                await self.finish({"message": "Successfully deleted user"})


@ApiRoute("auth/login", ApiVersion.V1)
class LoginHandler(BaseAPIController):
    @redact_data_paths(paths=["/password"])
    async def post(self):
        data = escape.json_decode(self.request.body)

        username = data.get("username", "")
        if not username:
            self.set_status(400)
            await self.finish({"message": "Username missing"})
            return

        password = data.get("password", "")
        if not password:
            self.set_status(400)
            await self.finish({"message": "Password missing"})
            return

        with self.make_session() as session:
            async with NamedLockRegistry.acquire(f"UserLock::{username}"):
                user = session.scalars(
                    select(User).where(User.username == username)
                ).first()
                if not user:
                    self.set_status(401)
                    await self.finish({"message": "Invalid username/password"})
                    return

                password_equal = await PasswordService.verify_password(
                    password, user.password
                )

                if password_equal:
                    session_id = data.get("session_id", "")
                    if session_id:
                        ws_session: Session = session.get(Session, session_id)
                        # session_id comes from the request body and uuids are
                        # not secret, so only an unowned client is attached here,
                        # and nothing is ever released from this path. A browser
                        # that really switches user is settled by its WebSocket
                        # AUTHENTICATE (the WS controller's ownership rules).
                        if ws_session and ws_session.user_id is None:
                            assign_session_user(ws_session, user.id)
                    user.last_login = datetime.now(tz=timezone.utc)
                    user.last_seen = datetime.now(tz=timezone.utc)
                    session.commit()

                    # Create JWT token
                    access_token = self.application.jwt_service.create_access_token(
                        data={
                            "user_id": user.id,
                        },
                    )

                    self.set_status(200)
                    await self.finish(
                        {
                            "message": "Successful log in",
                            "access_token": access_token,
                            "token_type": "bearer",
                        }
                    )
                else:
                    self.set_status(401)
                    await self.finish({"message": "Invalid username/password"})


@ApiRoute("auth/logout", ApiVersion.V1)
class LogoutHandler(BaseAPIController):
    def _log_out_client(self, session_id: str) -> None:
        """Detach the current user from their WebSocket client *session_id*.

        Marks every connection using that uuid (for example a tab and its
        browser-duplicated copy) as logged out, then releases the client's
        edit/cut lock and live-show leadership (with the usual broadcasts). The
        row keeps its owner: a different user who later logs in on this tab is
        moved to a fresh client uuid rather than inheriting this one. Only acts
        on a client that belongs to the current user, so logout can't be used
        against someone else's client.

        :param session_id: The client uuid sent by the logging-out page.
        """
        user_id = self.current_user["id"]
        try:
            exists, owner_id = row_owner(self.application, session_id)
            owns_client = exists and owner_id == user_id
        except Exception:
            get_logger().exception(
                f"Logout of user {user_id}: could not look up client "
                f"{session_id}; nothing was changed on it"
            )
            return
        if not owns_client:
            return
        for ws_controller in holders(self.application, session_id):
            ws_controller.current_user_id = None
        try:
            release_session_privileges(self.application, session_id, "user logged out")
        except Exception:
            # Its connections are already logged out, so the lock and leadership
            # can't be used; start the grace deadline so they are released when
            # it expires (finalise releases a row held only by unauthenticated
            # connections).
            schedule_disconnect_deadline(self.application, session_id)
            get_logger().exception(
                f"Logout of user {user_id}: could not release client "
                f"{session_id} now; its connections are logged out, and its lock "
                f"and leadership are released when its grace deadline expires"
            )

    @api_authenticated
    @allow_when_password_required
    async def post(self):
        data = escape.json_decode(self.request.body)

        if self.current_user:
            # Revoke the JWT first, so a failure below can never leave the token
            # valid while the client believes it has logged out.
            auth_header = self.request.headers.get("Authorization", "")
            token = self.application.jwt_service.get_token_from_authorization_header(
                auth_header
            )
            await self.application.jwt_service.revoke_token(token)

            session_id = data.get("session_id", "")
            if session_id:
                # Logs its own failures, each saying how far it got.
                self._log_out_client(session_id)

            self.set_status(200)
            await self.finish({"message": "Successfully logged out"})
        else:
            self.set_status(401)
            await self.finish({"message": "No user logged in"})


@ApiRoute("auth/refresh-token", ApiVersion.V1)
class RefreshTokenHandler(BaseAPIController):
    @api_authenticated
    async def post(self):
        """Generate a new access token using the current authentication"""
        access_token = self.application.jwt_service.create_access_token(
            data={
                "user_id": self.current_user["id"],
            },
        )

        self.set_status(200)
        await self.finish({"access_token": access_token, "token_type": "bearer"})


@ApiRoute("auth/users", ApiVersion.V1)
class UsersHandler(BaseAPIController):
    @api_authenticated
    @require_admin
    def get(self):
        user_schema = UserSchema()
        with self.make_session() as session:
            users = session.scalars(select(User)).all()
            self.set_status(200)
            self.finish({"users": [user_schema.dump(u) for u in users]})


@ApiRoute("auth", ApiVersion.V1)
class AuthHandler(BaseAPIController):
    @allow_when_password_required
    def get(self):
        self.set_status(200)
        self.finish(self.current_user if self.current_user else {})


@ApiRoute("auth/change-password", ApiVersion.V1)
class PasswordChangeController(BaseAPIController):
    """Self-service password change endpoint"""

    @api_authenticated
    @allow_when_password_required
    @redact_data_paths(paths=["/old_password", "/new_password"])
    async def patch(self):
        """
        Change authenticated user's password.

        Request body: {old_password: str, new_password: str}
        old_password is optional if requires_password_change=True

        :return: 200 on success, 401 if old password wrong, 400 if new password invalid
        """
        data = escape.json_decode(self.request.body)
        old_password = data.get("old_password", "")
        new_password = data.get("new_password", "")

        if not new_password:
            self.set_status(400)
            await self.finish({"message": "New password is required"})
            return

        with self.make_session() as session:
            user = session.get(User, self.current_user["id"])
            if not user:
                self.set_status(404)
                await self.finish({"message": "User not found"})
                return

            if not user.requires_password_change:
                if not old_password:
                    self.set_status(400)
                    await self.finish({"message": "Old password is required"})
                    return

                password_matches = await PasswordService.verify_password(
                    old_password, user.password
                )
                if not password_matches:
                    self.set_status(401)
                    await self.finish({"message": "Current password is incorrect"})
                    return

            try:
                # Increment token_version to invalidate old tokens, but don't
                # broadcast logout since we're providing a new token for all sessions
                await self.application.user_service.change_password(
                    session,
                    user,
                    new_password,
                    invalidate_tokens=True,
                    force_logout_sessions=False,
                )
            except ValueError as e:
                self.set_status(400)
                await self.finish({"message": str(e)})
                return

            # Generate new JWT token with updated token_version
            new_token = self.application.jwt_service.create_access_token(
                data={"user_id": user.id}
            )

            # Broadcast new token to all user's sessions for seamless re-auth
            await self.application.user_service.refresh_token_all_sessions(
                user, new_token
            )

            self.set_status(200)
            await self.finish(
                {
                    "message": "Password changed successfully",
                    "access_token": new_token,
                    "token_type": "bearer",
                }
            )


@ApiRoute("auth/reset-password", ApiVersion.V1)
class AdminPasswordResetController(BaseAPIController):
    """Admin-initiated password reset endpoint"""

    @api_authenticated
    @require_admin
    async def post(self):
        """
        Reset a user's password to a temporary password (admin only).

        Generates a temporary password and forces the user to change it on next login.
        Admins cannot reset their own password via this endpoint.

        Request body: {user_id: int}

        :return: 200 with temporary password on success, 400 if validation fails
        """
        data = escape.json_decode(self.request.body)
        user_id = data.get("user_id")

        if not user_id:
            self.set_status(400)
            await self.finish({"message": "user_id is required"})
            return

        with self.make_session() as session:
            target_user = session.get(User, int(user_id))
            if not target_user:
                self.set_status(404)
                await self.finish({"message": "User not found"})
                return

            if target_user.id == self.current_user["id"]:
                self.set_status(400)
                await self.finish(
                    {"message": "Cannot reset your own password via admin endpoint"}
                )
                return

            # Generate temporary password
            temp_password = PasswordService.generate_temporary_password()

            # Change the password and force password change on next login
            try:
                await self.application.user_service.change_password(
                    session,
                    target_user,
                    temp_password,
                    invalidate_tokens=True,
                    requires_password_change=True,
                )
            except ValueError as e:
                self.set_status(400)
                await self.finish({"message": str(e)})
                return

            self.set_status(200)
            await self.finish(
                {
                    "message": "Password reset successfully",
                    "temporary_password": temp_password,
                }
            )
