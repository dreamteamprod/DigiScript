from tornado import escape

from models.show import Show
from models.stage import Scenery
from rbac.role import Role
from schemas.schemas import ScenerySchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/stage/scenery", ApiVersion.V1)
class SceneryController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        scenery_schema = ScenerySchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
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

                new_scenery = Scenery(
                    show_id=show.id, name=name, description=description
                )
                session.add(new_scenery)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"id": new_scenery.id, "message": "Successfully added scenery"}
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

                    description = data.get("description", "")
                    entry.description = description

                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully updated scenery"})

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

                scenery_id = data.get("id", None)
                if not scenery_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry = session.get(Scenery, scenery_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted scenery"})

                    await self.application.ws_send_to_all(
                        "GET_SCENERY_LIST", "GET_SCENERY_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 scenery not found"})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
