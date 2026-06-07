from datetime import datetime, timezone

from sqlalchemy import select
from tornado import escape

from models.session import Session
from models.user import User
from registry.named_locks import NamedLockRegistry
from services.password_service import PasswordService
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import (
    allow_when_password_required,
    api_authenticated,
    redact_data_paths,
)


@ApiRoute("auth", ApiVersion.V2)
class AuthV2Controller(BaseAPIController):
    @allow_when_password_required
    def get(self):
        self.set_status(200)
        self.finish(self.current_user if self.current_user else {})


@ApiRoute("auth/login", ApiVersion.V2)
class AuthLoginV2Controller(BaseAPIController):
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
                        if ws_session:
                            ws_session.user = user
                    user.last_login = datetime.now(tz=timezone.utc)
                    user.last_seen = datetime.now(tz=timezone.utc)
                    session.commit()

                    access_token = self.application.jwt_service.create_access_token(
                        data={"user_id": user.id}
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


@ApiRoute("auth/logout", ApiVersion.V2)
class AuthLogoutV2Controller(BaseAPIController):
    @api_authenticated
    @allow_when_password_required
    async def post(self):
        data = escape.json_decode(self.request.body)

        if self.current_user:
            session_id = data.get("session_id", "")
            if session_id:
                with self.make_session() as session:
                    ws_session: Session = session.get(Session, session_id)
                    if ws_session:
                        ws_session.user = None
                        session.commit()

            ws_controller = self.application.get_ws(session_id)
            if ws_controller and hasattr(ws_controller, "current_user_id"):
                ws_controller.current_user_id = None

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


@ApiRoute("auth/refresh-token", ApiVersion.V2)
class AuthRefreshTokenV2Controller(BaseAPIController):
    @api_authenticated
    async def post(self):
        access_token = self.application.jwt_service.create_access_token(
            data={"user_id": self.current_user["id"]}
        )

        self.set_status(200)
        await self.finish({"access_token": access_token, "token_type": "bearer"})
