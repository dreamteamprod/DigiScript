from typing import List

from tornado import escape

from models.cue import CueType
from models.script import StageDirectionStyle
from models.user import UserOverrides
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import api_authenticated


@ApiRoute("user/settings/stage_direction_overrides", ApiVersion.V1)
class StageDirectionOverridesController(BaseAPIController):
    @api_authenticated
    def get(self):
        with self.make_session() as session:
            overrides: List[UserOverrides] = UserOverrides.get_by_type(
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
            style_to_override = session.get(StageDirectionStyle, style_id)
            if not style_to_override:
                self.set_status(404)
                await self.finish({"message": "Stage direction style not found"})
                return

            user_style = UserOverrides.create_for_user(
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
            entry: UserOverrides = session.get(UserOverrides, settings_id)
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
        settings_id = self.get_argument("id", None)
        if not settings_id:
            self.set_status(400)
            await self.finish({"message": "ID missing"})
            return

        with self.make_session() as session:
            entry: UserOverrides = session.get(UserOverrides, int(settings_id))
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


@ApiRoute("user/settings/cue_colour_overrides", ApiVersion.V1)
class CueColourOverridesController(BaseAPIController):
    @api_authenticated
    def get(self):
        with self.make_session() as session:
            overrides: List[UserOverrides] = UserOverrides.get_by_type(
                self.current_user["id"], CueType, session
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
        cue_type_id: str = data.get("cueTypeId", None)
        if not cue_type_id:
            self.set_status(400)
            await self.finish({"message": "Cue type ID missing"})
            return

        colour: str = data.get("colour", None)
        if not colour:
            self.set_status(400)
            await self.finish({"message": "Colour missing"})
            return

        with self.make_session() as session:
            cue_type_to_override = session.get(CueType, cue_type_id)
            if not cue_type_to_override:
                self.set_status(404)
                await self.finish({"message": "Cue type not found"})
                return

            user_override = UserOverrides.create_for_user(
                user_id=self.current_user["id"],
                settings_type="cuetypes",
                settings_data={
                    "id": cue_type_id,
                    "colour": colour,
                },
            )
            session.add(user_override)
            session.commit()

            self.set_status(200)
            await self.finish(
                {
                    "id": user_override.id,
                    "message": "Successfully added cue colour override",
                }
            )

            await self.application.ws_send_to_user(
                self.current_user["id"],
                "NOOP",
                "GET_CUE_COLOUR_OVERRIDES",
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
            entry: UserOverrides = session.get(UserOverrides, settings_id)
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
                    {"message": "Successfully edited cue colour override"}
                )

                await self.application.ws_send_to_user(
                    self.current_user["id"],
                    "NOOP",
                    "GET_CUE_COLOUR_OVERRIDES",
                    {},
                )
            else:
                self.set_status(404)
                await self.finish(
                    {"message": "Cue colour override not found"}
                )

    @api_authenticated
    async def delete(self):
        settings_id = self.get_argument("id", None)
        if not settings_id:
            self.set_status(400)
            await self.finish({"message": "ID missing"})
            return

        with self.make_session() as session:
            entry: UserOverrides = session.get(UserOverrides, int(settings_id))
            if entry:
                if entry.user_id != self.current_user["id"]:
                    self.set_status(403)
                    await self.finish()

                session.delete(entry)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"message": "Successfully deleted cue colour override"}
                )

                await self.application.ws_send_to_user(
                    self.current_user["id"],
                    "NOOP",
                    "GET_CUE_COLOUR_OVERRIDES",
                    {},
                )
            else:
                self.set_status(404)
                await self.finish(
                    {"message": "Cue colour override not found"}
                )