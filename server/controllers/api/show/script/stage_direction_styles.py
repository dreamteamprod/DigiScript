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


VALID_TEXT_FORMATS = ("default", "upper", "lower")


def validate_style_fields(data):
    """
    Validate stage direction style fields from request data.

    :param data: Request data dictionary
    :returns: Tuple of (error_message, validated_fields) - error_message is None if valid
    """
    text_format = data.get("textFormat", None)
    if not text_format or text_format not in VALID_TEXT_FORMATS:
        return ERROR_TEXT_FORMAT_INVALID, None

    text_colour = data.get("textColour", None)
    if not text_colour:
        return ERROR_TEXT_COLOUR_MISSING, None

    enable_background_colour = data.get("enableBackgroundColour", False)
    background_colour = data.get("backgroundColour", None)
    if enable_background_colour and not background_colour:
        return ERROR_BACKGROUND_COLOUR_MISSING, None

    return None, {
        "bold": data.get("bold", False),
        "italic": data.get("italic", False),
        "underline": data.get("underline", False),
        "text_format": text_format,
        "text_colour": text_colour,
        "enable_background_colour": enable_background_colour,
        "background_colour": background_colour,
    }


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

                error, fields = validate_style_fields(data)
                if error:
                    self.set_status(400)
                    await self.finish({"message": error})
                    return

                new_style = StageDirectionStyle(
                    script_id=script.id,
                    description=description,
                    **fields,
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

                error, fields = validate_style_fields(data)
                if error:
                    self.set_status(400)
                    await self.finish({"message": error})
                    return

                style.description = description
                for key, value in fields.items():
                    setattr(style, key, value)
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
