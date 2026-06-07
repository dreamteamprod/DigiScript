from datetime import datetime, timezone

from sqlalchemy import select
from tornado import escape

from models.user import User
from registry.named_locks import NamedLockRegistry
from schemas.schemas import UserSchema
from services.password_service import PasswordService
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import (
    api_authenticated,
    no_live_session,
    redact_data_paths,
    require_admin,
)


@ApiRoute("users", ApiVersion.V2)
class UsersV2Controller(BaseAPIController):
    EDITABLE_FIELDS = {"is_admin"}

    @api_authenticated
    @require_admin
    def get(self):
        user_schema = UserSchema()
        with self.make_session() as session:
            users = session.scalars(select(User)).all()
            self.set_status(200)
            self.finish({"users": [user_schema.dump(u) for u in users]})

    @redact_data_paths(paths=["/password", "/confirmPassword"])
    async def post(self):
        with self.make_session() as session:
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

    @api_authenticated
    @require_admin
    async def patch(self):
        user_id = self.get_argument("id", None)
        if not user_id:
            self.set_status(400)
            await self.finish({"message": "Id missing"})
            return

        data = escape.json_decode(self.request.body)

        with self.make_session() as session:
            user: User = session.get(User, int(user_id))
            if not user:
                self.set_status(404)
                await self.finish({"message": "User not found"})
                return

            if user.id == self.current_user["id"]:
                self.set_status(400)
                await self.finish({"message": "Cannot edit your own account"})
                return

            if "is_admin" in data and not data["is_admin"] and user.is_admin:
                all_admins = session.scalars(
                    select(User).where(User.is_admin.is_(True))
                ).all()
                if len(all_admins) <= 1:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Cannot remove admin from the only admin user"}
                    )
                    return

            for field in self.EDITABLE_FIELDS:
                if field in data:
                    setattr(user, field, data[field])

            session.commit()

        self.set_status(200)
        await self.application.ws_send_to_all("NOOP", "GET_USERS", {})
        await self.finish({"message": "Successfully updated user"})

    @api_authenticated
    @require_admin
    @no_live_session
    async def delete(self):
        user_id = self.get_argument("id", None)
        if not user_id:
            self.set_status(400)
            await self.finish({"message": "Id missing"})
            return

        with self.make_session() as session:
            user_to_delete: User = session.get(User, int(user_id))
            if not user_to_delete:
                self.set_status(404)
                await self.finish({"message": "User not found"})
                return

            if user_to_delete.id == self.current_user["id"]:
                self.set_status(400)
                await self.finish(
                    {"message": "Cannot delete currently authenticated user"}
                )
                return

            all_admins = session.scalars(
                select(User).where(User.is_admin.is_(True))
            ).all()
            if user_to_delete.is_admin and len(all_admins) <= 1:
                self.set_status(400)
                await self.finish({"message": "Cannot delete the only admin user"})
                return

            async with NamedLockRegistry.acquire(
                f"UserLock::{user_to_delete.username}"
            ):
                await self.application.user_service.force_logout_all_sessions(
                    session, user_to_delete
                )
                self.application.rbac.delete_actor(user_to_delete)
                session.delete(user_to_delete)
                session.commit()

                self.set_status(200)
                await self.application.ws_send_to_all("NOOP", "GET_USERS", {})
                await self.finish({"message": "Successfully deleted user"})
