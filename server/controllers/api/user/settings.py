from models.user import UserSettings
from schemas.schemas import UserSettingsSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import api_authenticated


@ApiRoute("user/settings", ApiVersion.V1)
class UserSettingsController(BaseAPIController):
    @api_authenticated
    async def get(self):
        schema = UserSettingsSchema()
        with self.make_session() as session:
            user_settings = session.get(UserSettings, self.current_user["id"])
            # If we do not have any settings for this user, then create them
            if not user_settings:
                user_settings = UserSettings(_user_id=self.current_user["id"])
                session.add(user_settings)
                session.commit()

            self.set_status(200)
            await self.finish(schema.dump(user_settings))
