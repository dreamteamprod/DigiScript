from sqlalchemy import select
from tornado import escape

from controllers.api.constants import (
    ERROR_ID_MISSING,
    ERROR_INVALID_ID,
    ERROR_NAME_MISSING,
    ERROR_PROP_NOT_FOUND,
    ERROR_PROP_TYPE_ID_MISSING,
    ERROR_PROP_TYPE_NOT_FOUND,
    ERROR_PROPS_ID_MISSING,
    ERROR_PROPS_NOT_FOUND,
    ERROR_SHOW_NOT_FOUND,
)
from controllers.api.show.stage.helpers import (
    handle_allocation_delete,
    handle_allocation_post,
)
from models.show import Show
from models.stage import Props, PropsAllocation, PropType
from rbac.role import Role
from schemas.schemas import PropsAllocationSchema, PropsSchema, PropTypeSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/stage/props/types", ApiVersion.V1)
class PropsTypesController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        prop_type_schema = PropTypeSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                prop_types = [prop_type_schema.dump(c) for c in show.prop_types]
                self.set_status(200)
                self.finish({"prop_types": prop_types})
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

            new_prop_type = PropType(
                show_id=show.id, name=name, description=description
            )
            session.add(new_prop_type)
            session.commit()

            self.set_status(200)
            await self.finish(
                {"id": new_prop_type.id, "message": "Successfully added prop type"}
            )

            await self.application.ws_send_to_all("NOOP", "GET_PROP_TYPES", {})

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

            entry: PropType = session.get(PropType, prop_type)
            if not entry:
                self.set_status(404)
                await self.finish({"message": ERROR_PROP_TYPE_NOT_FOUND})
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
            await self.finish({"message": "Successfully updated prop type"})

            await self.application.ws_send_to_all("NOOP", "GET_PROP_TYPES", {})

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

            prop_type_id_str = self.get_argument("id", None)
            if not prop_type_id_str:
                self.set_status(400)
                await self.finish({"message": ERROR_ID_MISSING})
                return

            try:
                prop_type_id = int(prop_type_id_str)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_ID})
                return

            entry = session.get(PropType, prop_type_id)
            if not entry:
                self.set_status(404)
                await self.finish({"message": ERROR_PROP_TYPE_NOT_FOUND})
                return

            session.delete(entry)
            session.commit()

            self.set_status(200)
            await self.finish({"message": "Successfully deleted prop type"})

            await self.application.ws_send_to_all("NOOP", "GET_PROP_TYPES", {})
            await self.application.ws_send_to_all("NOOP", "GET_PROPS_LIST", {})


@ApiRoute("show/stage/props", ApiVersion.V1)
class PropsController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        props_schema = PropsSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                props = [props_schema.dump(c) for c in show.props_list]
                self.set_status(200)
                self.finish({"props": props})
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

                prop_type_id = data.get("prop_type_id", None)
                if not prop_type_id:
                    self.set_status(400)
                    await self.finish({"message": ERROR_PROP_TYPE_ID_MISSING})
                    return
                try:
                    prop_type_id = int(prop_type_id)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": "Invalid prop type ID"})
                    return
                prop_type: PropType = session.get(PropType, prop_type_id)
                if not prop_type:
                    self.set_status(404)
                    await self.finish({"message": "Prop type not found"})
                    return
                if prop_type.show_id != show.id:
                    self.set_status(400)
                    await self.finish({"message": "Invalid prop type for show"})
                    return

                description = data.get("description", "")

                new_props = Props(
                    show_id=show.id,
                    name=name,
                    description=description,
                    prop_type_id=prop_type.id,
                )
                session.add(new_props)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"id": new_props.id, "message": "Successfully added props"}
                )

                await self.application.ws_send_to_all("NOOP", "GET_PROPS_LIST", {})
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

                props = data.get("id", None)
                if not props:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                entry: Props = session.get(Props, props)
                if entry:
                    name = data.get("name", None)
                    if not name:
                        self.set_status(400)
                        await self.finish({"message": ERROR_NAME_MISSING})
                        return
                    entry.name = name

                    prop_type_id = data.get("prop_type_id", None)
                    if not prop_type_id:
                        self.set_status(400)
                        await self.finish({"message": ERROR_PROP_TYPE_ID_MISSING})
                        return
                    try:
                        prop_type_id = int(prop_type_id)
                    except ValueError:
                        self.set_status(400)
                        await self.finish({"message": "Invalid prop type ID"})
                        return
                    prop_type: PropType = session.get(PropType, prop_type_id)
                    if not prop_type:
                        self.set_status(404)
                        await self.finish({"message": "Prop type not found"})
                        return
                    if prop_type.show_id != show.id:
                        self.set_status(400)
                        await self.finish({"message": "Invalid prop type for show"})
                        return
                    entry.prop_type_id = prop_type.id

                    description = data.get("description", "")
                    entry.description = description

                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully updated props"})

                    await self.application.ws_send_to_all("NOOP", "GET_PROPS_LIST", {})
                else:
                    self.set_status(404)
                    await self.finish({"message": ERROR_PROP_NOT_FOUND})
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

                props_id_str = self.get_argument("id", None)
                if not props_id_str:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                try:
                    props_id = int(props_id_str)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": ERROR_INVALID_ID})
                    return

                entry = session.get(Props, props_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted props"})

                    await self.application.ws_send_to_all("NOOP", "GET_PROPS_LIST", {})
                else:
                    self.set_status(404)
                    await self.finish({"message": ERROR_PROPS_NOT_FOUND})
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})


@ApiRoute("show/stage/props/allocations", ApiVersion.V1)
class PropsAllocationController(BaseAPIController):
    """Controller for managing props allocations to scenes."""

    @requires_show
    def get(self):
        """Get all props allocations for the current show."""
        current_show = self.get_current_show()
        show_id = current_show["id"]
        allocation_schema = PropsAllocationSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                allocations = session.scalars(
                    select(PropsAllocation)
                    .join(Props, PropsAllocation.props_id == Props.id)
                    .where(Props.show_id == show_id)
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
        """Create a new props allocation."""
        await handle_allocation_post(
            self,
            item_model=Props,
            item_id_key="props_id",
            allocation_model=PropsAllocation,
            allocation_item_fk="props_id",
            ws_action="GET_PROPS_ALLOCATIONS",
            error_item_id_missing=ERROR_PROPS_ID_MISSING,
            error_item_not_found=ERROR_PROP_NOT_FOUND,
            allocation_exists_message="Allocation already exists for this prop and scene",
        )

    @requires_show
    @no_live_session
    async def delete(self):
        """Delete a props allocation by ID (query parameter)."""
        await handle_allocation_delete(
            self,
            item_model=Props,
            allocation_model=PropsAllocation,
            allocation_item_fk="props_id",
            ws_action="GET_PROPS_ALLOCATIONS",
        )
