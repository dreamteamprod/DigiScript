from models.user import User
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.user_admin import generate_api_token, revoke_api_token
from utils.web.web_decorators import (
    api_authenticated,
)


@ApiRoute("auth/api-token/generate", ApiVersion.V1)
class ApiTokenGenerateController(BaseAPIController):
    @api_authenticated
    async def post(self):
        """Generate a new API token for the authenticated user"""
        await generate_api_token(self)


@ApiRoute("auth/api-token/revoke", ApiVersion.V1)
class ApiTokenRevokeController(BaseAPIController):
    @api_authenticated
    async def post(self):
        """Revoke the API token for the authenticated user"""
        await revoke_api_token(self)


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
