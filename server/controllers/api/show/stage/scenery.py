from sqlalchemy import select
from tornado import escape

from controllers.api.constants import (
    ERROR_CAST_MEMBER_NOT_FOUND,
    ERROR_ID_MISSING,
    ERROR_INVALID_ID,
    ERROR_NAME_MISSING,
    ERROR_SCENERY_ID_MISSING,
    ERROR_SCENERY_NOT_FOUND,
    ERROR_SCENERY_TYPE_ID_MISSING,
    ERROR_SCENERY_TYPE_NOT_FOUND,
    ERROR_SHOW_NOT_FOUND,
)
from controllers.api.show.stage.helpers import (
    handle_allocation_delete,
    handle_allocation_post,
)
from models.show import Show
from models.stage import Scenery, SceneryAllocation, SceneryType
from rbac.role import Role
from schemas.schemas import SceneryAllocationSchema, ScenerySchema, SceneryTypeSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/stage/scenery/types", ApiVersion.V1)
class SceneryTypesController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        scenery_type_schema = SceneryTypeSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                scenery_types = [
                    scenery_type_schema.dump(c) for c in show.scenery_types
                ]
                self.set_status(200)
                self.finish({"scenery_types": scenery_types})
            else:
                self.set_status(404)
                self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return
            self.requires_role(show, Role.WRITE)
            data = escape.json_decode(self.request.body)

            name = data.get("name", None)
            if not name:
                self.set_status(400)
                await self.finish({"message": ERROR_NAME_MISSING})
                return

            description = data.get("description", "")

            new_scenery_type = SceneryType(
                show_id=show.id, name=name, description=description
            )
            session.add(new_scenery_type)
            session.commit()

            self.set_status(200)
            await self.finish(
                {
                    "id": new_scenery_type.id,
                    "message": "Successfully added scenery type",
                }
            )

            await self.application.ws_send_to_all("NOOP", "GET_SCENERY_TYPES", {})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return
            self.requires_role(show, Role.WRITE)
            data = escape.json_decode(self.request.body)

            prop_type = data.get("id", None)
            if not prop_type:
                self.set_status(400)
                await self.finish({"message": ERROR_ID_MISSING})
                return

            entry: SceneryType = session.get(SceneryType, prop_type)
            if not entry:
                self.set_status(404)
                await self.finish({"message": ERROR_SCENERY_TYPE_NOT_FOUND})
                return

            name = data.get("name", None)
            description = data.get("description", "")
            if not name:
                self.set_status(400)
                await self.finish({"message": ERROR_NAME_MISSING})
                return

            entry.name = name
            entry.description = description
            session.commit()

            self.set_status(200)
            await self.finish({"message": "Successfully updated scenery type"})

            await self.application.ws_send_to_all("NOOP", "GET_SCENERY_TYPES", {})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return
            self.requires_role(show, Role.WRITE)

            scenery_type_id_str = self.get_argument("id", None)
            if not scenery_type_id_str:
                self.set_status(400)
                await self.finish({"message": ERROR_ID_MISSING})
                return

            try:
                scenery_type_id = int(scenery_type_id_str)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_ID})
                return

            entry = session.get(SceneryType, scenery_type_id)
            if not entry:
                self.set_status(404)
                await self.finish({"message": ERROR_SCENERY_TYPE_NOT_FOUND})
                return

            session.delete(entry)
            session.commit()

            self.set_status(200)
            await self.finish({"message": "Successfully deleted scenery type"})

            await self.application.ws_send_to_all("NOOP", "GET_SCENERY_TYPES", {})
            await self.application.ws_send_to_all("NOOP", "GET_SCENERY_LIST", {})


@ApiRoute("show/stage/scenery", ApiVersion.V1)
class SceneryController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        scenery_schema = ScenerySchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                scenery = [scenery_schema.dump(c) for c in show.scenery_list]
                self.set_status(200)
                self.finish({"scenery": scenery})
            else:
                self.set_status(404)
                self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                name = data.get("name", None)
                if not name:
                    self.set_status(400)
                    await self.finish({"message": ERROR_NAME_MISSING})
                    return

                scenery_type_id = data.get("scenery_type_id", None)
                if not scenery_type_id:
                    self.set_status(400)
                    await self.finish({"message": ERROR_SCENERY_TYPE_ID_MISSING})
                    return
                try:
                    scenery_type_id = int(scenery_type_id)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": "Scenery prop type ID"})
                    return
                scenery_type: SceneryType = session.get(SceneryType, scenery_type_id)
                if not scenery_type:
                    self.set_status(404)
                    await self.finish({"message": "Scenery type not found"})
                    return
                if scenery_type.show_id != show.id:
                    self.set_status(400)
                    await self.finish({"message": "Invalid scenery type for show"})
                    return

                description = data.get("description", "")

                new_scenery = Scenery(
                    show_id=show.id,
                    name=name,
                    description=description,
                    scenery_type_id=scenery_type.id,
                )
                session.add(new_scenery)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"id": new_scenery.id, "message": "Successfully added scenery"}
                )

                await self.application.ws_send_to_all("NOOP", "GET_SCENERY_LIST", {})
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                scenery = data.get("id", None)
                if not scenery:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                entry: Scenery = session.get(Scenery, scenery)
                if entry:
                    name = data.get("name", None)
                    if not name:
                        self.set_status(400)
                        await self.finish({"message": ERROR_NAME_MISSING})
                        return
                    entry.name = name

                    scenery_type_id = data.get("scenery_type_id", None)
                    if not scenery_type_id:
                        self.set_status(400)
                        await self.finish({"message": ERROR_SCENERY_TYPE_ID_MISSING})
                        return
                    try:
                        scenery_type_id = int(scenery_type_id)
                    except ValueError:
                        self.set_status(400)
                        await self.finish({"message": "Scenery prop type ID"})
                        return
                    scenery_type: SceneryType = session.get(
                        SceneryType, scenery_type_id
                    )
                    if not scenery_type:
                        self.set_status(404)
                        await self.finish({"message": "Scenery type not found"})
                        return
                    if scenery_type.show_id != show.id:
                        self.set_status(400)
                        await self.finish({"message": "Invalid scenery type for show"})
                        return
                    entry.scenery_type_id = scenery_type.id

                    description = data.get("description", "")
                    entry.description = description

                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully updated scenery"})

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SCENERY_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": ERROR_CAST_MEMBER_NOT_FOUND})
                    return
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)

                scenery_id_str = self.get_argument("id", None)
                if not scenery_id_str:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                try:
                    scenery_id = int(scenery_id_str)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": ERROR_INVALID_ID})
                    return

                entry = session.get(Scenery, scenery_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted scenery"})

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SCENERY_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": ERROR_SCENERY_NOT_FOUND})
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})


@ApiRoute("show/stage/scenery/allocations", ApiVersion.V1)
class SceneryAllocationController(BaseAPIController):
    """Controller for managing scenery allocations to scenes."""

    @requires_show
    def get(self):
        """Get all scenery allocations for the current show."""
        current_show = self.get_current_show()
        show_id = current_show["id"]
        allocation_schema = SceneryAllocationSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                allocations = session.scalars(
                    select(SceneryAllocation)
                    .join(Scenery, SceneryAllocation.scenery_id == Scenery.id)
                    .where(Scenery.show_id == show_id)
                ).all()
                allocations = [allocation_schema.dump(a) for a in allocations]
                self.set_status(200)
                self.finish({"allocations": allocations})
            else:
                self.set_status(404)
                self.finish({"message": ERROR_SHOW_NOT_FOUND})

    @requires_show
    @no_live_session
    async def post(self):
        """Create a new scenery allocation."""
        await handle_allocation_post(
            self,
            item_model=Scenery,
            item_id_key="scenery_id",
            allocation_model=SceneryAllocation,
            allocation_item_fk="scenery_id",
            ws_action="GET_SCENERY_ALLOCATIONS",
            error_item_id_missing=ERROR_SCENERY_ID_MISSING,
            error_item_not_found=ERROR_SCENERY_NOT_FOUND,
            allocation_exists_message="Allocation already exists for this scenery and scene",
        )

    @requires_show
    @no_live_session
    async def delete(self):
        """Delete a scenery allocation by ID (query parameter)."""
        await handle_allocation_delete(
            self,
            item_model=Scenery,
            allocation_model=SceneryAllocation,
            allocation_item_fk="scenery_id",
            ws_action="GET_SCENERY_ALLOCATIONS",
        )
