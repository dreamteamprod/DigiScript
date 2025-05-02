from tornado import escape

from digi_server.logger import get_logger
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

    @api_authenticated
    async def patch(self):
        log = get_logger()
        data = escape.json_decode(self.request.body)
        with self.make_session() as session:
            user_settings = session.get(UserSettings, self.current_user["id"])
            if not user_settings:
                # If we do not have any settings for this user, then create them
                user_settings = UserSettings(_user_id=self.current_user["id"])
                session.add(user_settings)
                session.flush()

            for k, v in data.items():
                if hasattr(user_settings, k):
                    if k[0] == "_":
                        log.warning(
                            f"User attempted to set protected setting: {k}. Ignoring."
                        )
                    else:
                        setattr(user_settings, k, v)
                else:
                    log.warning(
                        f"User attempted to set unknown setting: {k}. Ignoring."
                    )

            session.commit()

        await self.application.ws_send_to_user(
            self.current_user["id"], "NO_OP", "GET_USER_SETTINGS", {}
        )
        self.set_status(200)
        self.write({"message": "User settings updated"})
