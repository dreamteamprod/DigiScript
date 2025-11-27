from datetime import datetime, timezone
import secrets

import bcrypt
from tornado import escape, gen
from tornado.ioloop import IOLoop

from models.session import Session
from models.user import User
from registry.named_locks import NamedLockRegistry
from schemas.schemas import UserSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import (
    api_authenticated,
    no_live_session,
    require_admin,
    requires_show,
)


@ApiRoute("auth/create", ApiVersion.V1)
class UserCreateController(BaseAPIController):

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
        if len(password) < 6:
            self.set_status(400)
            await self.finish(
                {"message": "Password must be at least 6 characters long"}
            )
            return

        is_admin = data.get("is_admin", False)

        with self.make_session() as session:
            conflict_user = (
                session.query(User).filter(User.username == username).first()
            )
            if conflict_user:
                self.set_status(400)
                await self.finish({"message": "Username already taken"})
                return

            hashed_password = await IOLoop.current().run_in_executor(
                None, bcrypt.hashpw, escape.utf8(password), bcrypt.gensalt()
            )
            hashed_password = escape.to_unicode(hashed_password)

            session.add(
                User(
                    username=username,
                    password=hashed_password,
                    is_admin=is_admin,
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
            user_to_delete: User = session.query(User).get(int(user_to_delete))
            if not user_to_delete:
                self.set_status(400)
                await self.finish({"message": "Could not find user to delete"})
                return

            if user_to_delete.is_admin:
                self.set_status(400)
                await self.finish({"message": "Cannot delete admin user"})
                return

            async with NamedLockRegistry.acquire(
                f"UserLock::{user_to_delete.username}"
            ):
                # First, log out all sessions for this user
                await self.application.ws_send_to_user(
                    user_to_delete.id, "NOOP", "USER_LOGOUT", {}
                )

                # Then really make sure we have logged out the user for all sessions (basically,
                # wait for the websocket ops to finish)
                session_logout_attempts = 0
                user_sessions = (
                    session.query(Session)
                    .filter(Session.user_id == user_to_delete.id)
                    .all()
                )
                while user_sessions and session_logout_attempts < 5:
                    for user_session in user_sessions:
                        ws_session = self.application.get_ws(user_session.internal_id)
                        await ws_session.write_message(
                            {"OP": "NOOP", "DATA": "{}", "ACTION": "USER_LOGOUT"}
                        )
                        ws_session.current_user_id = None
                    await gen.sleep(0.2)
                    user_sessions = (
                        session.query(Session)
                        .filter(Session.user_id == user_to_delete.id)
                        .all()
                    )
                    session_logout_attempts += 1

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
                user = session.query(User).filter(User.username == username).first()
                if not user:
                    self.set_status(401)
                    await self.finish({"message": "Invalid username/password"})
                    return

                password_equal = await IOLoop.current().run_in_executor(
                    None,
                    bcrypt.checkpw,
                    escape.utf8(password),
                    escape.utf8(user.password),
                )

                if password_equal:
                    session_id = data.get("session_id", "")
                    if session_id:
                        ws_session: Session = session.query(Session).get(session_id)
                        if ws_session:
                            ws_session.user = user
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
    @api_authenticated
    async def post(self):
        data = escape.json_decode(self.request.body)

        if self.current_user:
            session_id = data.get("session_id", "")
            if session_id:
                with self.make_session() as session:
                    ws_session: Session = session.query(Session).get(session_id)
                    if ws_session:
                        ws_session.user = None
                        session.commit()

            # Update the WebSocket controller if it exists
            ws_controller = self.application.get_ws(session_id)
            if ws_controller and hasattr(ws_controller, "current_user_id"):
                ws_controller.current_user_id = None

            # Revoke the JWT
            auth_header = self.request.headers.get("Authorization", "")
            token = self.application.jwt_service.get_token_from_authorization_header(
                auth_header
            )
            await self.application.jwt_service.revoke_token(token)

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
    @requires_show
    def get(self):
        user_schema = UserSchema()
        with self.make_session() as session:
            users = session.query(User).all()
            self.set_status(200)
            self.finish({"users": [user_schema.dump(u) for u in users]})


@ApiRoute("auth", ApiVersion.V1)
class AuthHandler(BaseAPIController):
    def get(self):
        self.set_status(200)
        self.finish(self.current_user if self.current_user else {})


@ApiRoute("auth/api-token/generate", ApiVersion.V1)
class ApiTokenGenerateController(BaseAPIController):
    @api_authenticated
    async def post(self):
        """Generate a new API token for the authenticated user"""
        with self.make_session() as session:
            user = session.query(User).get(self.current_user["id"])
            if not user:
                self.set_status(404)
                await self.finish({"message": "User not found"})
                return

            # Generate a secure random token (plain text to return to user)
            new_token = secrets.token_urlsafe(32)

            # Hash the token before storing (like passwords)
            hashed_token = await IOLoop.current().run_in_executor(
                None, bcrypt.hashpw, escape.utf8(new_token), bcrypt.gensalt()
            )
            hashed_token = escape.to_unicode(hashed_token)

            user.api_token = hashed_token
            session.commit()

            self.set_status(200)
            await self.finish(
                {
                    "message": "API token generated successfully",
                    "api_token": new_token,
                }
            )


@ApiRoute("auth/api-token/revoke", ApiVersion.V1)
class ApiTokenRevokeController(BaseAPIController):
    @api_authenticated
    async def post(self):
        """Revoke the API token for the authenticated user"""
        with self.make_session() as session:
            user = session.query(User).get(self.current_user["id"])
            if not user:
                self.set_status(404)
                await self.finish({"message": "User not found"})
                return

            if not user.api_token:
                self.set_status(400)
                await self.finish({"message": "No API token to revoke"})
                return

            user.api_token = None
            session.commit()

            self.set_status(200)
            await self.finish({"message": "API token revoked successfully"})


@ApiRoute("auth/api-token", ApiVersion.V1)
class ApiTokenController(BaseAPIController):
    @api_authenticated
    def get(self):
        """Check if the authenticated user has an API token"""
        with self.make_session() as session:
            user = session.query(User).get(self.current_user["id"])
            if not user:
                self.set_status(404)
                self.finish({"message": "User not found"})
                return

            self.set_status(200)
            self.finish({"has_token": user.api_token is not None})
