from sqlalchemy import select
from tornado import escape

from models.show import Scene, Show
from models.stage import Scenery, SceneryAllocation, SceneryType
from rbac.role import Role
from schemas.schemas import SceneryAllocationSchema, ScenerySchema, SceneryTypeSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/stage/scenery/types", ApiVersion.V1)
class PropsTypesController(BaseAPIController):
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
                self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
                return
            self.requires_role(show, Role.WRITE)
            data = escape.json_decode(self.request.body)

            name = data.get("name", None)
            if not name:
                self.set_status(400)
                await self.finish({"message": "Name missing"})
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
                await self.finish({"message": "404 show not found"})
                return
            self.requires_role(show, Role.WRITE)
            data = escape.json_decode(self.request.body)

            prop_type = data.get("id", None)
            if not prop_type:
                self.set_status(400)
                await self.finish({"message": "ID missing"})
                return

            entry: SceneryType = session.get(SceneryType, prop_type)
            if not entry:
                self.set_status(404)
                await self.finish({"message": "404 scenery type not found"})
                return

            name = data.get("name", None)
            description = data.get("description", "")
            if not name:
                self.set_status(400)
                await self.finish({"message": "Name missing"})
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
                await self.finish({"message": "404 show not found"})
                return
            self.requires_role(show, Role.WRITE)

            scenery_type_id_str = self.get_argument("id", None)
            if not scenery_type_id_str:
                self.set_status(400)
                await self.finish({"message": "ID missing"})
                return

            try:
                scenery_type_id = int(scenery_type_id_str)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": "Invalid ID"})
                return

            entry = session.get(SceneryType, scenery_type_id)
            if not entry:
                self.set_status(404)
                await self.finish({"message": "404 scenery type not found"})
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
                self.finish({"message": "404 show not found"})

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
                    await self.finish({"message": "Name missing"})
                    return

                scenery_type_id = data.get("scenery_type_id", None)
                if not scenery_type_id:
                    self.set_status(400)
                    await self.finish({"message": "Scenery type ID missing"})
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
                await self.finish({"message": "404 show not found"})

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
                    await self.finish({"message": "ID missing"})
                    return

                entry: Scenery = session.get(Scenery, scenery)
                if entry:
                    name = data.get("name", None)
                    if not name:
                        self.set_status(400)
                        await self.finish({"message": "Name missing"})
                        return
                    entry.name = name

                    scenery_type_id = data.get("scenery_type_id", None)
                    if not scenery_type_id:
                        self.set_status(400)
                        await self.finish({"message": "Scenery type ID missing"})
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
                    await self.finish({"message": "404 cast member not found"})
                    return
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

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
                    await self.finish({"message": "ID missing"})
                    return

                try:
                    scenery_id = int(scenery_id_str)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": "Invalid ID"})
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
                    await self.finish({"message": "404 scenery not found"})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


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
                self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def post(self):
        """Create a new scenery allocation."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
                return

            self.requires_role(show, Role.WRITE)
            data = escape.json_decode(self.request.body)

            # Validate scenery_id
            scenery_id = data.get("scenery_id", None)
            if scenery_id is None:
                self.set_status(400)
                await self.finish({"message": "scenery_id missing"})
                return

            try:
                scenery_id = int(scenery_id)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": "Invalid scenery_id"})
                return

            scenery: Scenery = session.get(Scenery, scenery_id)
            if not scenery:
                self.set_status(404)
                await self.finish({"message": "404 scenery not found"})
                return

            if scenery.show_id != show_id:
                self.set_status(404)
                await self.finish({"message": "404 scenery not found"})
                return

            # Validate scene_id
            scene_id = data.get("scene_id", None)
            if scene_id is None:
                self.set_status(400)
                await self.finish({"message": "scene_id missing"})
                return

            try:
                scene_id = int(scene_id)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": "Invalid scene_id"})
                return

            scene: Scene = session.get(Scene, scene_id)
            if not scene:
                self.set_status(404)
                await self.finish({"message": "404 scene not found"})
                return

            if scene.show_id != show_id:
                self.set_status(404)
                await self.finish({"message": "404 scene not found"})
                return

            # Check for duplicate allocation
            existing = session.scalars(
                select(SceneryAllocation).where(
                    SceneryAllocation.scenery_id == scenery_id,
                    SceneryAllocation.scene_id == scene_id,
                )
            ).first()
            if existing:
                self.set_status(400)
                await self.finish(
                    {"message": "Allocation already exists for this scenery and scene"}
                )
                return

            new_allocation = SceneryAllocation(scenery_id=scenery_id, scene_id=scene_id)
            session.add(new_allocation)
            session.commit()

            self.set_status(200)
            await self.finish(
                {"id": new_allocation.id, "message": "Successfully added allocation"}
            )

            await self.application.ws_send_to_all("NOOP", "GET_SCENERY_ALLOCATIONS", {})

    @requires_show
    @no_live_session
    async def delete(self):
        """Delete a scenery allocation by ID (query parameter)."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
                return

            self.requires_role(show, Role.WRITE)

            allocation_id_str = self.get_argument("id", None)
            if not allocation_id_str:
                self.set_status(400)
                await self.finish({"message": "ID missing"})
                return

            try:
                allocation_id = int(allocation_id_str)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": "Invalid ID"})
                return

            allocation: SceneryAllocation = session.get(
                SceneryAllocation, allocation_id
            )
            if not allocation:
                self.set_status(404)
                await self.finish({"message": "404 allocation not found"})
                return

            # Verify the allocation belongs to scenery in this show
            scenery: Scenery = session.get(Scenery, allocation.scenery_id)
            if not scenery or scenery.show_id != show_id:
                self.set_status(404)
                await self.finish({"message": "404 allocation not found"})
                return

            session.delete(allocation)
            session.commit()

            self.set_status(200)
            await self.finish({"message": "Successfully deleted allocation"})

            await self.application.ws_send_to_all("NOOP", "GET_SCENERY_ALLOCATIONS", {})
