from tornado import escape

from models.show import Crew, Show
from rbac.role import Role
from schemas.schemas import CrewSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/stage/crew", ApiVersion.V1)
class CastController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        crew_schema = CrewSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                crew = [crew_schema.dump(c) for c in show.crew_list]
                self.set_status(200)
                self.finish({"crew": crew})
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

                first_name = data.get("firstName", None)
                if not first_name:
                    self.set_status(400)
                    await self.finish({"message": "First name missing"})
                    return

                last_name = data.get("lastName", None)
                if not last_name:
                    self.set_status(400)
                    await self.finish({"message": "Last name missing"})
                    return

                new_crew = Crew(
                    show_id=show.id, first_name=first_name, last_name=last_name
                )
                session.add(new_crew)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"id": new_crew.id, "message": "Successfully added crew member"}
                )

                await self.application.ws_send_to_all(
                    "GET_CREW_LIST", "GET_CREW_LIST", {}
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

                crew_id = data.get("id", None)
                if not crew_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry: Crew = session.get(Crew, crew_id)
                if entry:
                    first_name = data.get("firstName", None)
                    if not first_name:
                        self.set_status(400)
                        await self.finish({"message": "First name missing"})
                        return
                    entry.first_name = first_name

                    last_name = data.get("lastName", None)
                    if not last_name:
                        self.set_status(400)
                        await self.finish({"message": "Last name missing"})
                        return
                    entry.last_name = last_name

                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully updated crew member"})

                    await self.application.ws_send_to_all(
                        "GET_CREW_LIST", "GET_CREW_LIST", {}
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

                crew_id = data.get("id", None)
                if not crew_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry = session.get(Crew, crew_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted crew member"})

                    await self.application.ws_send_to_all(
                        "GET_CREW_LIST", "GET_CREW_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 crew member not found"})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
