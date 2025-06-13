from collections import defaultdict

from tornado import escape

from models.script import Script, ScriptLine, ScriptRevision
from models.show import Cast, Character, Show
from rbac.role import Role
from schemas.schemas import CastSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/cast", ApiVersion.V1)
class CastController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        cast_schema = CastSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                cast = [cast_schema.dump(c) for c in show.cast_list]
                self.set_status(200)
                self.finish({"cast": cast})
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

                new_cast = Cast(
                    show_id=show.id, first_name=first_name, last_name=last_name
                )
                session.add(new_cast)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"id": new_cast.id, "message": "Successfully added cast member"}
                )

                await self.application.ws_send_to_all(
                    "GET_CAST_LIST", "GET_CAST_LIST", {}
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

                cast_id = data.get("id", None)
                if not cast_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry: Cast = session.get(Cast, cast_id)
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
                    await self.finish({"message": "Successfully updated cast member"})

                    await self.application.ws_send_to_all(
                        "GET_CAST_LIST", "GET_CAST_LIST", {}
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

                cast_id = data.get("id", None)
                if not cast_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry = session.get(Cast, cast_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted cast member"})

                    await self.application.ws_send_to_all(
                        "GET_CAST_LIST", "GET_CAST_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 cast member not found"})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


@ApiRoute("show/cast/stats", ApiVersion.V1)
class CharacterStatsController(BaseAPIController):
    async def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.query(Show).get(show_id)
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision
                    )
                else:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Script does not have a current revision"}
                    )
                    return

                line_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
                for line_association in revision.line_associations:
                    line: ScriptLine = line_association.line
                    if line.stage_direction:
                        continue
                    for line_part in line.line_parts:
                        if line_part.line_part_cuts is not None:
                            continue
                        if line_part.character_id:
                            character = session.get(Character, line_part.character_id)
                            if character.played_by:
                                line_counts[character.played_by][line.act_id][
                                    line.scene_id
                                ] += 1
                        elif line_part.character_group_id:
                            for character in line_part.character_group.characters:
                                if character.played_by:
                                    line_counts[character.played_by][line.act_id][
                                        line.scene_id
                                    ] += 1

                self.set_status(200)
                await self.finish({"line_counts": line_counts})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
