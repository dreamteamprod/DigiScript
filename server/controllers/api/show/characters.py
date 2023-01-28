from tornado import escape

from models.show import Show, Cast, Character, CharacterGroup
from schemas.schemas import CharacterSchema, CharacterGroupSchema
from utils.base_controller import BaseAPIController
from utils.web_decorators import requires_show, no_live_session
from utils.route import ApiRoute, ApiVersion


@ApiRoute('show/character', ApiVersion.v1)
class CharacterController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        character_schema = CharacterSchema()

        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    characters = [character_schema.dump(c) for c in show.character_list]
                    self.set_status(200)
                    self.finish({'characters': characters})
                else:
                    self.set_status(404)
                    self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            self.write({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show: Show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    name = data.get('name', None)
                    if not name:
                        self.set_status(400)
                        await self.finish({'message': 'Name missing'})
                        return

                    description = data.get('description', None)
                    played_by = data.get('played_by', None)
                    if played_by:
                        cast_member = session.query(Cast).get(played_by)
                        if not cast_member:
                            self.set_status(404)
                            await self.finish({'message': '404 cast member found'})
                            return

                    session.add(Character(show_id=show.id, name=name, description=description,
                                          played_by=played_by))
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully added cast member'})

                    await self.application.ws_send_to_all('NOOP', 'GET_CHARACTER_LIST', {})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show: Show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    character_id = data.get('id', None)
                    if not character_id:
                        self.set_status(400)
                        await self.finish({'message': 'ID missing'})
                        return

                    entry: Character = session.get(Character, character_id)
                    if entry:
                        name = data.get('name', None)
                        if not name:
                            self.set_status(400)
                            await self.finish({'message': 'Name missing'})
                            return
                        entry.name = name

                        description = data.get('description', None)
                        entry.description = description

                        played_by = data.get('played_by', None)
                        if played_by:
                            cast_member = session.query(Cast).get(played_by)
                            if not cast_member:
                                self.set_status(404)
                                await self.finish({'message': '404 cast member found'})
                                return
                        entry.played_by = played_by

                        session.commit()

                        self.set_status(200)
                        await self.finish({'message': 'Successfully updated character'})

                        await self.application.ws_send_to_all('NOOP', 'GET_CHARACTER_LIST', {})
                    else:
                        self.set_status(404)
                        await self.finish({'message': '404 character not found'})
                        return
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show: Show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    character_id = data.get('id', None)
                    if not character_id:
                        self.set_status(400)
                        await self.finish({'message': 'ID missing'})
                        return

                    entry: Character = session.get(Character, character_id)
                    if entry:
                        session.delete(entry)
                        session.commit()

                        self.set_status(200)
                        await self.finish({'message': 'Successfully deleted character'})

                        await self.application.ws_send_to_all('NOOP', 'GET_CHARACTER_LIST', {})
                    else:
                        self.set_status(404)
                        await self.finish({'message': '404 character not found'})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})


@ApiRoute('show/character/group', ApiVersion.v1)
class CharacterGroupController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        character_group_schema = CharacterGroupSchema()

        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    character_groups = [character_group_schema.dump(c)
                                        for c in show.character_group_list]
                    self.set_status(200)
                    self.finish({'character_groups': character_groups})
                else:
                    self.set_status(404)
                    self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            self.write({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    name = data.get('name', None)
                    if not name:
                        self.set_status(400)
                        await self.finish({'message': 'Name missing'})
                        return

                    description = data.get('description', None)
                    character_list = data.get('characters', [])

                    character_model_list = []
                    for character_id in character_list:
                        character = session.query(Character).get(character_id)
                        if not character:
                            self.set_status(404)
                            await self.finish({'message': f'Character {character_id} not found'})
                            return
                        character_model_list.append(character)

                    session.add(CharacterGroup(
                        show_id=show_id,
                        name=name,
                        description=description,
                        characters=character_model_list))
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully added new character group'})

                    await self.application.ws_send_to_all('NOOP', 'GET_CHARACTER_GROUP_LIST', {})

                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
                    return
        else:
            self.set_status(404)
            self.write({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show: Show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    character_group_id = data.get('id', None)
                    if not character_group_id:
                        self.set_status(400)
                        await self.finish({'message': 'ID missing'})
                        return

                    entry: CharacterGroup = session.get(CharacterGroup, character_group_id)
                    if entry:
                        session.delete(entry)
                        session.commit()

                        self.set_status(200)
                        await self.finish({'message': 'Successfully deleted character group'})

                        await self.application.ws_send_to_all('NOOP',
                                                              'GET_CHARACTER_GROUP_LIST',
                                                              {})
                    else:
                        self.set_status(404)
                        await self.finish({'message': '404 character not found'})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show: Show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    character_group_id = data.get('id', None)
                    if not character_group_id:
                        self.set_status(400)
                        await self.finish({'message': 'ID missing'})
                        return

                    entry: CharacterGroup = session.get(CharacterGroup, character_group_id)
                    if entry:
                        name = data.get('name', None)
                        if not name:
                            self.set_status(400)
                            await self.finish({'message': 'Name missing'})
                            return
                        entry.name = name

                        entry.description = data.get('description', None)

                        character_list = data.get('characters', [])
                        character_model_list = []
                        for character_id in character_list:
                            character = session.query(Character).get(character_id)
                            if not character:
                                self.set_status(404)
                                await self.finish({
                                    'message': f'Character {character_id} not found'
                                })
                                return
                            character_model_list.append(character)
                        entry.characters = character_model_list

                        session.commit()

                        self.set_status(200)
                        await self.finish({'message': 'Successfully updated character group'})

                        await self.application.ws_send_to_all(
                            'NOOP', 'GET_CHARACTER_GROUP_LIST', {})
                    else:
                        self.set_status(404)
                        await self.finish({'message': '404 character group not found'})
                        return
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})
