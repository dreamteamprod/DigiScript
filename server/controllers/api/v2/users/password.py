from tornado import escape

from models.user import User
from services.password_service import PasswordService
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import (
    allow_when_password_required,
    api_authenticated,
    redact_data_paths,
    require_admin,
)


@ApiRoute("users/password", ApiVersion.V2)
class UsersPasswordV2Controller(BaseAPIController):
    @api_authenticated
    @allow_when_password_required
    @redact_data_paths(paths=["/old_password", "/new_password"])
    async def patch(self):
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

            new_token = self.application.jwt_service.create_access_token(
                data={"user_id": user.id}
            )
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


@ApiRoute("users/password/reset", ApiVersion.V2)
class UsersPasswordResetV2Controller(BaseAPIController):
    @api_authenticated
    @require_admin
    async def post(self):
        user_id = self.get_argument("id", None)
        if not user_id:
            self.set_status(400)
            await self.finish({"message": "Id missing"})
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

            temp_password = PasswordService.generate_temporary_password()

            try:
                await self.application.user_service.change_password(
                    session, target_user, temp_password, invalidate_tokens=True
                )
            except ValueError as e:
                self.set_status(400)
                await self.finish({"message": str(e)})
                return

            target_user.requires_password_change = True
            session.commit()

            self.set_status(200)
            await self.finish(
                {
                    "message": "Password reset successfully",
                    "temporary_password": temp_password,
                }
            )
