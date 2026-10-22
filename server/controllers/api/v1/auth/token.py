from models.user import User
from utils.web.api_keys import ApiKeyService
from utils.web.auth_audit import audit
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

            # Key is a random secret; only its SHA-256 digest is stored
            new_token, user.api_token = ApiKeyService.generate()
            session.commit()
            self.application.jwt_service.api_keys.invalidate()

            audit(
                "api_token_generate",
                "success",
                username=self.current_user.get("username"),
                user_id=user.id,
                remote_ip=self.request.remote_ip,
            )
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
                audit(
                    "api_token_revoke",
                    "failure",
                    username=self.current_user.get("username"),
                    user_id=user.id,
                    remote_ip=self.request.remote_ip,
                    detail="reason=no_token",
                )
                self.set_status(400)
                await self.finish({"message": "No API token to revoke"})
                return

            user.api_token = None
            session.commit()
            self.application.jwt_service.api_keys.invalidate()

            audit(
                "api_token_revoke",
                "success",
                username=self.current_user.get("username"),
                user_id=user.id,
                remote_ip=self.request.remote_ip,
            )
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
