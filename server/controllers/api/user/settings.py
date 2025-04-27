from typing import List

from tornado import escape

from models.script import StageDirectionStyle
from models.user import UserSettings
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import api_authenticated


@ApiRoute("user/settings/stage_direction_overrides", ApiVersion.V1)
class UserStageDirectionOverridesController(BaseAPIController):
    @api_authenticated
    def get(self):
        with self.make_session() as session:
            overrides: List[UserSettings] = UserSettings.get_by_type(
                self.current_user["id"], StageDirectionStyle, session
            )
            self.set_status(200)
            self.finish(
                {
                    "overrides": [
                        {"id": override.id, "settings": override.settings_dict}
                        for override in overrides
                    ]
                }
            )

    @api_authenticated
    async def post(self):
        data = escape.json_decode(self.request.body)
        style_id: str = data.get("styleId", None)
        if not style_id:
            self.set_status(400)
            await self.finish({"message": "Style ID missing"})
            return

        bold: bool = data.get("bold", False)
        italic: bool = data.get("italic", False)
        underline: bool = data.get("underline", False)

        text_format: str = data.get("textFormat", None)
        if not text_format or text_format not in ["default", "upper", "lower"]:
            self.set_status(400)
            await self.finish({"message": "Text format missing or invalid"})
            return

        text_colour: str = data.get("textColour", None)
        if not text_colour:
            self.set_status(400)
            await self.finish({"message": "Text colour missing"})
            return

        enable_background_colour: bool = data.get("enableBackgroundColour", False)
        background_colour: str = data.get("backgroundColour", None)
        if enable_background_colour and not background_colour:
            self.set_status(400)
            await self.finish({"message": "Background colour missing"})
            return

        with self.make_session() as session:
            style_to_override = session.query(StageDirectionStyle).get(style_id)
            if not style_to_override:
                self.set_status(404)
                await self.finish({"message": "Stage direction style not found"})
                return

            user_style = UserSettings.create_for_user(
                user_id=self.current_user["id"],
                settings_type="stage_direction_styles",
                settings_data={
                    "id": style_id,
                    "bold": bold,
                    "italic": italic,
                    "underline": underline,
                    "text_format": text_format,
                    "text_colour": text_colour,
                    "enable_background_colour": enable_background_colour,
                    "background_colour": background_colour,
                },
            )
            session.add(user_style)
            session.commit()

            self.set_status(200)
            await self.finish(
                {
                    "id": user_style.id,
                    "message": "Successfully added stage direction style override",
                }
            )

            await self.application.ws_send_to_user(
                self.current_user["id"],
                "NOOP",
                "GET_STAGE_DIRECTION_STYLE_OVERRIDES",
                {},
            )

    @api_authenticated
    async def patch(self):
        data = escape.json_decode(self.request.body)
        settings_id = data.get("id", None)
        if not settings_id:
            self.set_status(400)
            await self.finish({"message": "ID missing"})
            return

        with self.make_session() as session:
            entry: UserSettings = session.get(UserSettings, settings_id)
            if entry:
                if entry.user_id != self.current_user["id"]:
                    self.set_status(403)
                    await self.finish()

                merge_settings = data.copy()
                del merge_settings["id"]
                entry.update_settings(merge_settings)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"message": "Successfully edited stage direction style override"}
                )

                await self.application.ws_send_to_user(
                    self.current_user["id"],
                    "NOOP",
                    "GET_STAGE_DIRECTION_STYLE_OVERRIDES",
                    {},
                )
            else:
                self.set_status(404)
                await self.finish(
                    {"message": "Stage direction style override not found"}
                )

    @api_authenticated
    async def delete(self):
        data = escape.json_decode(self.request.body)
        with self.make_session() as session:
            settings_id = data.get("id", None)
            if not settings_id:
                self.set_status(400)
                await self.finish({"message": "ID missing"})
                return

            entry: UserSettings = session.get(UserSettings, settings_id)
            if entry:
                if entry.user_id != self.current_user["id"]:
                    self.set_status(403)
                    await self.finish()

                session.delete(entry)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"message": "Successfully deleted stage direction style override"}
                )

                await self.application.ws_send_to_user(
                    self.current_user["id"],
                    "NOOP",
                    "GET_STAGE_DIRECTION_STYLE_OVERRIDES",
                    {},
                )
            else:
                self.set_status(404)
                await self.finish(
                    {"message": "Stage direction style override not found"}
                )
