from sqlalchemy import select

from models.user import User
from registry.named_locks import USER_CREATE_LOCK, NamedLockRegistry
from schemas.schemas import UserSchema
from utils.web.auth_audit import actor, audit
from utils.web.base_controller import BaseAPIController
from utils.web.json_body import get_json_object
from utils.web.route import ApiRoute, ApiVersion
from utils.web.user_admin import create_user, delete_user
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
        # The has-any-users check and the insert form one critical section;
        # otherwise concurrent first-run requests could each create an admin.
        async with NamedLockRegistry.acquire(USER_CREATE_LOCK):
            await create_user(self)

    @api_authenticated
    @require_admin
    async def patch(self):
        user_id = self.get_argument("id", None)
        if not user_id:
            self.set_status(400)
            await self.finish({"message": "Id missing"})
            return

        data = get_json_object(self)

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
                    audit(
                        "user_update",
                        "failure",
                        detail=f"target_user_id={user.id} reason=only_admin",
                        **actor(self),
                    )
                    self.set_status(400)
                    await self.finish(
                        {"message": "Cannot remove admin from the only admin user"}
                    )
                    return

            changed = []
            for field in self.EDITABLE_FIELDS:
                if field in data:
                    setattr(user, field, data[field])
                    changed.append(f"{field}={data[field]!r}")

            session.commit()
            audit(
                "user_update",
                "success",
                detail=f"target_user_id={user.id} changed={','.join(changed) or 'none'}",
                **actor(self),
            )

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

            await delete_user(self, session, user_to_delete)
