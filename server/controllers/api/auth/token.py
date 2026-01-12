import secrets

from models.user import User
from services.password_service import PasswordService
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import (
    api_authenticated,
)


@ApiRoute("auth/api-token/generate", ApiVersion.V1)
class ApiTokenGenerateController(BaseAPIController):
    @api_authenticated
    async def post(self):
        """Generate a new API token for the authenticated user"""
        with self.make_session() as session:
            user = session.get(User, self.current_user["id"])
            if not user:
                self.set_status(404)
                await self.finish({"message": "User not found"})
                return

            # Generate a secure random token (plain text to return to user)
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


@ApiRoute("auth/api-token/revoke", ApiVersion.V1)
class ApiTokenRevokeController(BaseAPIController):
    @api_authenticated
    async def post(self):
        """Revoke the API token for the authenticated user"""
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


@ApiRoute("auth/api-token", ApiVersion.V1)
class ApiTokenController(BaseAPIController):
    @api_authenticated
    def get(self):
        """Check if the authenticated user has an API token"""
        with self.make_session() as session:
            user = session.get(User, self.current_user["id"])
            if not user:
                self.set_status(404)
                self.finish({"message": "User not found"})
                return

            self.set_status(200)
            self.finish({"has_token": user.api_token is not None})
