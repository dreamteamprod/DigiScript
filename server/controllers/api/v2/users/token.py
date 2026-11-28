from models.user import User
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.user_admin import generate_api_token, revoke_api_token
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
        await generate_api_token(self)

    @api_authenticated
    async def delete(self):
        await revoke_api_token(self)
