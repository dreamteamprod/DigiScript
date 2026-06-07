from sqlalchemy import func, select
from tornado import escape

from controllers.api.constants import (
    ERROR_COLOUR_MISSING,
    ERROR_ID_MISSING,
    ERROR_SHOW_NOT_FOUND,
    ERROR_TAG_NAME_EXISTS,
    ERROR_TAG_NAME_MISSING,
    ERROR_TAG_NOT_FOUND,
)
from models.session import SessionTag
from models.show import Show
from rbac.role import Role
from schemas.schemas import ShowSessionTagSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/session/tags", ApiVersion.V1)
class SessionTagsController(BaseAPIController):
    @requires_show
    def get(self):
        """List all session tags for the current show."""
        current_show = self.get_current_show()
        show_id = current_show["id"]
        tag_schema = ShowSessionTagSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                tags = session.scalars(
                    select(SessionTag).where(SessionTag.show_id == show.id)
                ).all()
                tags = [tag_schema.dump(t) for t in tags]
                self.set_status(200)
                self.finish({"tags": tags})
            else:
                self.set_status(404)
                self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def post(self):
        """Create a new session tag."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                # Validate tag name
                tag = data.get("tag", None)
                if not tag:
                    self.set_status(400)
                    await self.finish({"message": ERROR_TAG_NAME_MISSING})
                    return

                # Validate colour
                colour = data.get("colour", None)
                if not colour:
                    self.set_status(400)
                    await self.finish({"message": ERROR_COLOUR_MISSING})
                    return

                # Check case-insensitive uniqueness
                existing_tag = session.scalars(
                    select(SessionTag).where(
                        SessionTag.show_id == show_id,
                        func.lower(SessionTag.tag) == func.lower(tag),
                    )
                ).first()
                if existing_tag:
                    self.set_status(400)
                    await self.finish({"message": ERROR_TAG_NAME_EXISTS})
                    return

                # Create new tag
                new_tag = SessionTag(show_id=show_id, tag=tag, colour=colour)
                session.add(new_tag)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"id": new_tag.id, "message": "Successfully added session tag"}
                )

                await self.application.ws_send_to_all("NOOP", "GET_SESSION_TAGS", {})
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def patch(self):
        """Update an existing session tag."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                # Validate tag ID
                tag_id = data.get("id", None)
                if not tag_id:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                # Fetch existing tag
                tag_obj = session.get(SessionTag, tag_id)
                if not tag_obj:
                    self.set_status(404)
                    await self.finish({"message": ERROR_TAG_NOT_FOUND})
                    return

                # Validate tag name
                tag = data.get("tag", None)
                if not tag:
                    self.set_status(400)
                    await self.finish({"message": ERROR_TAG_NAME_MISSING})
                    return

                # Validate colour
                colour = data.get("colour", None)
                if not colour:
                    self.set_status(400)
                    await self.finish({"message": ERROR_COLOUR_MISSING})
                    return

                # Check case-insensitive uniqueness (excluding self)
                other_tag = session.scalars(
                    select(SessionTag).where(
                        SessionTag.show_id == show_id,
                        func.lower(SessionTag.tag) == func.lower(tag),
                        SessionTag.id != tag_id,
                    )
                ).first()
                if other_tag:
                    self.set_status(400)
                    await self.finish({"message": ERROR_TAG_NAME_EXISTS})
                    return

                # Update tag
                tag_obj.tag = tag
                tag_obj.colour = colour
                session.commit()

                self.set_status(200)
                await self.finish({"message": "Successfully updated session tag"})

                await self.application.ws_send_to_all("NOOP", "GET_SESSION_TAGS", {})
                await self.application.ws_send_to_all(
                    "NOOP", "GET_SHOW_SESSION_DATA", {}
                )
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def delete(self):
        """Delete a session tag."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)

                # Get tag ID from query parameter
                try:
                    tag_id: int = int(self.get_query_argument("id"))
                except Exception:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                # Fetch tag and delete
                tag_obj = session.get(SessionTag, tag_id)
                if tag_obj:
                    session.delete(tag_obj)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted session tag"})

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SESSION_TAGS", {}
                    )
                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SHOW_SESSION_DATA", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": ERROR_TAG_NOT_FOUND})
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})


@ApiRoute("show/session/tags/import", ApiVersion.V1)
class SessionTagImportController(BaseAPIController):
    @requires_show
    def get(self):
        """
        Return all session tags from all other shows, grouped by show.

        :returns: JSON with a ``tag_groups`` key containing a list of show objects,
            each with ``id``, ``name``, and ``tags`` fields.
        """
        current_show_id = self.get_current_show()["id"]
        schema = ShowSessionTagSchema()

        with self.make_session() as session:
            rows = session.execute(
                select(Show, SessionTag)
                .join(SessionTag, SessionTag.show_id == Show.id)
                .where(Show.id != current_show_id)
                .order_by(Show.id)
            ).all()

            shows_map: dict = {}
            for show, tag in rows:
                if show.id not in shows_map:
                    shows_map[show.id] = {
                        "id": show.id,
                        "name": show.name,
                        "tags": [],
                    }
                shows_map[show.id]["tags"].append(schema.dump(tag))

        self.set_status(200)
        self.finish({"tag_groups": list(shows_map.values())})
