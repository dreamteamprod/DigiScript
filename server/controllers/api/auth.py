from datetime import datetime

import bcrypt
from tornado import escape, web
from tornado.ioloop import IOLoop

from models.session import Session
from models.user import User
from schemas.schemas import UserSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import require_admin, requires_show


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

                self.set_secure_cookie("digiscript_user_id", str(user.id))
                self.set_status(200)
                await self.finish({"message": "Successful log in"})
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

            self.clear_cookie("digiscript_user_id")
            self.set_status(200)
            await self.finish({"message": "Successfully logged out"})
        else:
            self.set_status(401)
            await self.finish({"message": "No user logged in"})


@ApiRoute("auth/validate", ApiVersion.V1)
class AuthValidationHandler(BaseAPIController):
    @web.authenticated
    async def get(self):
        if self.current_user["is_admin"]:
            self.set_status(200)
            await self.finish({"message": "OK"})
        elif (
            self.current_show
            and self.current_user["show_id"] == self.current_show["id"]
        ):
            self.set_status(200)
            await self.finish({"message": "OK"})
        else:
            self.set_status(401)
            self.write({"message": "Not Authenticated"})


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
