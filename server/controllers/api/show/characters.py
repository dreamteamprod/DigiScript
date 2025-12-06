from collections import defaultdict

from tornado import escape

from models.script import Script, ScriptLine, ScriptRevision
from models.show import Cast, Character, CharacterGroup, Show
from rbac.role import Role
from schemas.schemas import CharacterGroupSchema, CharacterSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/character", ApiVersion.V1)
class CharacterController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        character_schema = CharacterSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                characters = [character_schema.dump(c) for c in show.character_list]
                self.set_status(200)
                self.finish({"characters": characters})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                name = data.get("name", None)
                if not name:
                    self.set_status(400)
                    await self.finish({"message": "Name missing"})
                    return

                description = data.get("description", None)
                played_by = data.get("played_by", None)
                if played_by:
                    cast_member = session.get(Cast, played_by)
                    if not cast_member:
                        self.set_status(404)
                        await self.finish({"message": "404 cast member found"})
                        return

                new_character = Character(
                    show_id=show.id,
                    name=name,
                    description=description,
                    played_by=played_by,
                )
                session.add(new_character)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {
                        "id": new_character.id,
                        "message": "Successfully added cast member",
                    }
                )

                await self.application.ws_send_to_all("NOOP", "GET_CHARACTER_LIST", {})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                character_id = data.get("id", None)
                if not character_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry: Character = session.get(Character, character_id)
                if entry:
                    name = data.get("name", None)
                    if not name:
                        self.set_status(400)
                        await self.finish({"message": "Name missing"})
                        return
                    entry.name = name

                    description = data.get("description", None)
                    entry.description = description

                    played_by = data.get("played_by", None)
                    if played_by:
                        cast_member = session.get(Cast, played_by)
                        if not cast_member:
                            self.set_status(404)
                            await self.finish({"message": "404 cast member found"})
                            return
                    entry.played_by = played_by

                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully updated character"})

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_CHARACTER_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 character not found"})
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
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                character_id = data.get("id", None)
                if not character_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry: Character = session.get(Character, character_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted character"})

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_CHARACTER_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 character not found"})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


@ApiRoute("show/character/stats", ApiVersion.V1)
class CharacterStatsController(BaseAPIController):
    async def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )

                if script.current_revision:
                    revision: ScriptRevision = session.get(ScriptRevision,
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
                            line_counts[line_part.character_id][line.act_id][
                                line.scene_id
                            ] += 1
                        elif line_part.character_group_id:
                            for character in line_part.character_group.characters:
                                line_counts[character.id][line.act_id][
                                    line.scene_id
                                ] += 1

                self.set_status(200)
                await self.finish({"line_counts": line_counts})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


@ApiRoute("show/character/group", ApiVersion.V1)
class CharacterGroupController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        character_group_schema = CharacterGroupSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                character_groups = [
                    character_group_schema.dump(c) for c in show.character_group_list
                ]
                self.set_status(200)
                self.finish({"character_groups": character_groups})
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

                description = data.get("description", None)
                character_list = data.get("characters", [])

                character_model_list = []
                for character_id in character_list:
                    character = session.get(Character, character_id)
                    if not character:
                        self.set_status(404)
                        await self.finish(
                            {"message": f"Character {character_id} not found"}
                        )
                        return
                    character_model_list.append(character)

                session.add(
                    CharacterGroup(
                        show_id=show_id,
                        name=name,
                        description=description,
                        characters=character_model_list,
                    )
                )
                session.commit()

                self.set_status(200)
                await self.finish({"message": "Successfully added new character group"})

                await self.application.ws_send_to_all(
                    "NOOP", "GET_CHARACTER_GROUP_LIST", {}
                )

            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                character_group_id = data.get("id", None)
                if not character_group_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry: CharacterGroup = session.get(CharacterGroup, character_group_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish(
                        {"message": "Successfully deleted character group"}
                    )

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_CHARACTER_GROUP_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 character not found"})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                character_group_id = data.get("id", None)
                if not character_group_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                entry: CharacterGroup = session.get(CharacterGroup, character_group_id)
                if entry:
                    name = data.get("name", None)
                    if not name:
                        self.set_status(400)
                        await self.finish({"message": "Name missing"})
                        return
                    entry.name = name

                    entry.description = data.get("description", None)

                    character_list = data.get("characters", [])
                    character_model_list = []
                    for character_id in character_list:
                        character = session.get(Character, character_id)
                        if not character:
                            self.set_status(404)
                            await self.finish(
                                {"message": f"Character {character_id} not found"}
                            )
                            return
                        character_model_list.append(character)
                    entry.characters = character_model_list

                    session.commit()

                    self.set_status(200)
                    await self.finish(
                        {"message": "Successfully updated character group"}
                    )

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_CHARACTER_GROUP_LIST", {}
                    )
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 character group not found"})
                    return
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
