from digi_server.logger import get_logger
from models.user import UserSettings
from schemas.schemas import UserSettingsSchema
from utils.web.base_controller import BaseAPIController
from utils.web.json_body import get_json_object
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import allow_when_password_required, api_authenticated


# Settings a user may change themselves. Anything else (including internal
# ``_``-prefixed columns and non-column attributes) is ignored.
EDITABLE_USER_SETTINGS = frozenset(
    {
        "enable_script_auto_save",
        "script_auto_save_interval",
        "cue_position_right",
        "script_text_alignment",
        "console_log_level",
        "character_mru_sort",
        "character_combined_dropdown",
        "preferred_ui",
        "table_page_sizes",
        "default_sd_text_colour",
        "default_sd_background_colour",
        "show_current_cue_footer",
    }
)


@ApiRoute("user/settings", ApiVersion.V1)
class UserSettingsController(BaseAPIController):
    @api_authenticated
    @allow_when_password_required
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
        data = get_json_object(self)
        with self.make_session() as session:
            user_settings = session.get(UserSettings, self.current_user["id"])
            if not user_settings:
                # If we do not have any settings for this user, then create them
                user_settings = UserSettings(_user_id=self.current_user["id"])
                session.add(user_settings)
                session.flush()

            for k, v in data.items():
                if k in EDITABLE_USER_SETTINGS:
                    setattr(user_settings, k, v)
                else:
                    log.warning(
                        f"User attempted to set non-editable setting: {k}. Ignoring."
                    )

            session.commit()

        await self.application.ws_send_to_user(
            self.current_user["id"], "NO_OP", "GET_USER_SETTINGS", {}
        )
        self.set_status(200)
        self.write({"message": "User settings updated"})
