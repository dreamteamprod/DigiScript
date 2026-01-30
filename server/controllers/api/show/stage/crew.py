from tornado import escape

from controllers.api.constants import (
    ERROR_CAST_MEMBER_NOT_FOUND,
    ERROR_CREW_NOT_FOUND,
    ERROR_FIRST_NAME_MISSING,
    ERROR_ID_MISSING,
    ERROR_INVALID_ID,
    ERROR_LAST_NAME_MISSING,
    ERROR_SHOW_NOT_FOUND,
)
from models.show import Show
from models.stage import Crew
from rbac.role import Role
from schemas.schemas import CrewSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/stage/crew", ApiVersion.V1)
class CrewController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        crew_schema = CrewSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                crew = [crew_schema.dump(c) for c in show.crew_list]
                self.set_status(200)
                self.finish({"crew": crew})
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

                first_name = data.get("firstName", None)
                if not first_name:
                    self.set_status(400)
                    await self.finish({"message": ERROR_FIRST_NAME_MISSING})
                    return

                last_name = data.get("lastName", None)
                if not last_name:
                    self.set_status(400)
                    await self.finish({"message": ERROR_LAST_NAME_MISSING})
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

                crew_id = data.get("id", None)
                if not crew_id:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                entry: Crew = session.get(Crew, crew_id)
                if entry:
                    first_name = data.get("firstName", None)
                    if not first_name:
                        self.set_status(400)
                        await self.finish({"message": ERROR_FIRST_NAME_MISSING})
                        return
                    entry.first_name = first_name

                    last_name = data.get("lastName", None)
                    if not last_name:
                        self.set_status(400)
                        await self.finish({"message": ERROR_LAST_NAME_MISSING})
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

                crew_id_str = self.get_argument("id", None)
                if not crew_id_str:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                try:
                    crew_id = int(crew_id_str)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": ERROR_INVALID_ID})
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
                    await self.finish({"message": ERROR_CREW_NOT_FOUND})
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
