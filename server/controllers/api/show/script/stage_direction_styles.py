from sqlalchemy import select
from tornado import escape

from controllers.api.constants import (
    ERROR_BACKGROUND_COLOUR_MISSING,
    ERROR_DESCRIPTION_MISSING,
    ERROR_ID_MISSING,
    ERROR_SHOW_NOT_FOUND,
    ERROR_STAGE_DIRECTION_STYLE_NOT_FOUND,
    ERROR_TEXT_COLOUR_MISSING,
    ERROR_TEXT_FORMAT_INVALID,
)
from models.script import Script, StageDirectionStyle
from models.show import Show
from rbac.role import Role
from schemas.schemas import StageDirectionStyleSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("/show/script/stage_direction_styles", ApiVersion.V1)
class StageDirectionStylesController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        stage_direction_style_schema = StageDirectionStyleSchema()
        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()
                stage_direction_styles = [
                    stage_direction_style_schema.dump(style)
                    for style in script.stage_direction_styles
                ]

                self.set_status(200)
                self.finish({"styles": stage_direction_styles})
            else:
                self.set_status(404)
                self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()
                self.requires_role(script, Role.WRITE)
                data = escape.json_decode(self.request.body)

                description: str = data.get("description", None)
                if not description:
                    self.set_status(400)
                    await self.finish({"message": ERROR_DESCRIPTION_MISSING})
                    return

                bold: bool = data.get("bold", False)
                italic: bool = data.get("italic", False)
                underline: bool = data.get("underline", False)

                text_format: str = data.get("textFormat", None)
                if not text_format or text_format not in ["default", "upper", "lower"]:
                    self.set_status(400)
                    await self.finish({"message": ERROR_TEXT_FORMAT_INVALID})
                    return

                text_colour: str = data.get("textColour", None)
                if not text_colour:
                    self.set_status(400)
                    await self.finish({"message": ERROR_TEXT_COLOUR_MISSING})
                    return

                enable_background_colour: bool = data.get(
                    "enableBackgroundColour", False
                )
                background_colour: str = data.get("backgroundColour", None)
                if enable_background_colour and not background_colour:
                    self.set_status(400)
                    await self.finish({"message": ERROR_BACKGROUND_COLOUR_MISSING})
                    return

                new_style = StageDirectionStyle(
                    script_id=script.id,
                    description=description,
                    bold=bold,
                    italic=italic,
                    underline=underline,
                    text_format=text_format,
                    text_colour=text_colour,
                    enable_background_colour=enable_background_colour,
                    background_colour=background_colour,
                )
                session.add(new_style)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {
                        "id": new_style.id,
                        "message": "Successfully added stage direction style",
                    }
                )

                await self.application.ws_send_to_all(
                    "NOOP", "GET_STAGE_DIRECTION_STYLES", {}
                )
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()
                self.requires_role(script, Role.WRITE)
                data = escape.json_decode(self.request.body)

                style_id = data.get("id", None)
                if not style_id:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                style: StageDirectionStyle = session.get(StageDirectionStyle, style_id)
                if not style:
                    self.set_status(404)
                    await self.finish(
                        {"message": ERROR_STAGE_DIRECTION_STYLE_NOT_FOUND}
                    )
                    return

                description: str = data.get("description", None)
                if not description:
                    self.set_status(400)
                    await self.finish({"message": ERROR_DESCRIPTION_MISSING})
                    return

                bold: bool = data.get("bold", False)
                italic: bool = data.get("italic", False)
                underline: bool = data.get("underline", False)

                text_format: str = data.get("textFormat", None)
                if not text_format or text_format not in ["default", "upper", "lower"]:
                    self.set_status(400)
                    await self.finish({"message": ERROR_TEXT_FORMAT_INVALID})
                    return

                text_colour: str = data.get("textColour", None)
                if not text_colour:
                    self.set_status(400)
                    await self.finish({"message": ERROR_TEXT_COLOUR_MISSING})
                    return

                enable_background_colour: bool = data.get(
                    "enableBackgroundColour", False
                )
                background_colour: str = data.get("backgroundColour", None)
                if enable_background_colour and not background_colour:
                    self.set_status(400)
                    await self.finish({"message": ERROR_BACKGROUND_COLOUR_MISSING})
                    return

                style.description = description
                style.bold = bold
                style.italic = italic
                style.underline = underline
                style.text_format = text_format
                style.text_colour = text_colour
                style.enable_background_colour = enable_background_colour
                style.background_colour = background_colour
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"message": "Successfully edited stage direction style"}
                )

                await self.application.ws_send_to_all(
                    "NOOP", "GET_STAGE_DIRECTION_STYLES", {}
                )
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()
                self.requires_role(script, Role.WRITE)
                data = escape.json_decode(self.request.body)

                style_id = data.get("id", None)
                if not style_id:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                entry: StageDirectionStyle = session.get(StageDirectionStyle, style_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish(
                        {"message": "Successfully deleted stage direction style"}
                    )

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_STAGE_DIRECTION_STYLES", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish(
                        {"message": ERROR_STAGE_DIRECTION_STYLE_NOT_FOUND}
                    )
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
