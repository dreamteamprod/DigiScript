from datetime import datetime, timedelta

import bcrypt
from tornado import escape, gen, web
from tornado.ioloop import IOLoop

from models.session import Session
from models.user import User
from registry.named_locks import NamedLockRegistry
from schemas.schemas import UserSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, require_admin, requires_show


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
    @web.authenticated
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
                    user.last_login = datetime.utcnow()
                    session.commit()

                    # Create JWT token
                    access_token = self.application.jwt_service.create_access_token(
                        data={
                            "user_id": user.id,
                        },
                        expires_delta=timedelta(minutes=120),
                    )

                    self.set_secure_cookie(
                        "jwt_token",
                        access_token,
                        httponly=True,
                        expires_days=5,  # Slightly longer than token expiry for better UX
                    )

                    # Keep setting the cookie for backward compatibility
                    self.set_secure_cookie("digiscript_user_id", str(user.id))
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
    @web.authenticated
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

            self.clear_cookie("jwt_token")
            # Clear cookie (for backward compatibility)
            self.clear_cookie("digiscript_user_id")
            self.set_status(200)
            await self.finish({"message": "Successfully logged out"})
        else:
            self.set_status(401)
            await self.finish({"message": "No user logged in"})


@ApiRoute("auth/refresh-token", ApiVersion.V1)
class RefreshTokenHandler(BaseAPIController):
    @web.authenticated
    async def post(self):
        """Generate a new access token using the current authentication"""
        if not self.current_user:
            self.set_status(401)
            await self.finish({"message": "Not authenticated"})
            return

        # Create a new JWT token with extended expiration
        access_token = self.application.jwt_service.create_access_token(
            data={
                "user_id": self.current_user["id"],
            },
            expires_delta=timedelta(minutes=120),
        )

        self.set_secure_cookie(
            "jwt_token",
            access_token,
            httponly=True,
            expires_days=5,  # Slightly longer than token expiry for better UX
        )

        self.set_status(200)
        await self.finish({"access_token": access_token, "token_type": "bearer"})


@ApiRoute("auth/users", ApiVersion.V1)
class UsersHandler(BaseAPIController):
    @web.authenticated
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
