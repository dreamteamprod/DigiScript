from tornado import escape

from controllers.base_controller import BaseAPIController
from models.models import Show, Character, Cast
from models.schemas import CharacterSchema
from utils.route import ApiRoute, ApiVersion


@ApiRoute('show/character', ApiVersion.v1)
class CharacterController(BaseAPIController):

    def get(self):
        show_id = self.get_query_argument('show_id', None)
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

    async def post(self):
        show_id = self.get_query_argument('show_id', None)
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

    async def patch(self):
        show_id = self.get_query_argument('show_id', None)
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

    async def delete(self):
        show_id = self.get_query_argument('show_id', None)
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
