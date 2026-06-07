import secrets

from models.user import User
from services.password_service import PasswordService
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import api_authenticated


@ApiRoute("users/token", ApiVersion.V2)
class UsersTokenV2Controller(BaseAPIController):
    @api_authenticated
    def get(self):
        with self.make_session() as session:
            user = session.get(User, self.current_user["id"])
            if not user:
                self.set_status(404)
                self.finish({"message": "User not found"})
                return

            self.set_status(200)
            self.finish({"has_token": user.api_token is not None})

    @api_authenticated
    async def post(self):
        with self.make_session() as session:
            user = session.get(User, self.current_user["id"])
            if not user:
                self.set_status(404)
                await self.finish({"message": "User not found"})
                return

            new_token = secrets.token_urlsafe(32)
            hashed_token = await PasswordService.hash_password(new_token)
            user.api_token = hashed_token
            session.commit()

            self.set_status(200)
            await self.finish(
                {
                    "message": "API token generated successfully",
                    "api_token": new_token,
                }
            )

    @api_authenticated
    async def delete(self):
        with self.make_session() as session:
            user = session.get(User, self.current_user["id"])
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
