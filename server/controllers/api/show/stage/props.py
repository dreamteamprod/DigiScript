from tornado import escape

from models.show import Show
from models.stage import Props
from rbac.role import Role
from schemas.schemas import PropsSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/stage/props", ApiVersion.V1)
class PropsController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        props_schema = PropsSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                props = [props_schema.dump(c) for c in show.props_list]
                self.set_status(200)
                self.finish({"props": props})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                name = data.get("name", None)
                if not name:
                    self.set_status(400)
                    await self.finish({"message": "Name missing"})
                    return

                description = data.get("description", "")

                new_props = Props(show_id=show.id, name=name, description=description)
                session.add(new_props)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"id": new_props.id, "message": "Successfully added props"}
                )

                await self.application.ws_send_to_all(
                    "GET_SCENERY_LIST", "GET_SCENERY_LIST", {}
                )
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                props = data.get("id", None)
                if not props:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry: Props = session.get(Props, props)
                if entry:
                    name = data.get("name", None)
                    if not name:
                        self.set_status(400)
                        await self.finish({"message": "Name missing"})
                        return
                    entry.name = name

                    description = data.get("description", "")
                    entry.description = description

                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully updated props"})

                    await self.application.ws_send_to_all(
                        "GET_SCENERY_LIST", "GET_SCENERY_LIST", {}
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
            show = session.query(Show).get(show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                props_id = data.get("id", None)
                if not props_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry = session.get(Props, props_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted props"})

                    await self.application.ws_send_to_all(
                        "GET_SCENERY_LIST", "GET_SCENERY_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 props not found"})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
