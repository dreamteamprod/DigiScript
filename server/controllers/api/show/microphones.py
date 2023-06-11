from typing import List

from tornado import escape

from models.mics import Microphone
from models.show import Show
from rbac.role import Role
from schemas.schemas import MicrophoneSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiVersion, ApiRoute
from utils.web.web_decorators import requires_show, no_live_session


@ApiRoute('show/microphones', ApiVersion.V1)
class MicrophoneController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']
        mic_schema = MicrophoneSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                scenes: List[Microphone] = session.query(Microphone).filter(
                    Microphone.show_id == show.id).all()
                scenes = [mic_schema.dump(c) for c in scenes]
                self.set_status(200)
                self.finish({'microphones': scenes})
            else:
                self.set_status(404)
                self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                name: str = data.get('name', None)
                if not name:
                    self.set_status(400)
                    await self.finish({'message': 'Name missing'})
                    return

                other_named = session.query(Microphone).filter(
                    Microphone.show_id == show_id,
                    Microphone.name == name).first()
                if other_named:
                    self.set_status(400)
                    await self.finish({'message': 'Name already taken'})
                    return

                description: str = data.get('description', None)

                session.add(Microphone(
                    show_id=show_id,
                    name=name,
                    description=description))
                session.commit()

                self.set_status(200)
                await self.finish({'message': 'Successfully added microphone'})

                await self.application.ws_send_to_all('NOOP', 'GET_MICROPHONE_LIST', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show: Show = session.query(Show).get(show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                microphone_id = data.get('id', None)
                if not microphone_id:
                    self.set_status(400)
                    await self.finish({'message': 'ID missing'})
                    return

                microphone: Microphone = session.query(Microphone).get(microphone_id)
                if not microphone:
                    self.set_status(404)
                    await self.finish({'message': '404 microphone not found'})
                    return

                name: str = data.get('name', None)
                if not name:
                    self.set_status(400)
                    await self.finish({'message': 'Name missing'})
                    return

                other_named = session.query(Microphone).filter(
                    Microphone.show_id == show_id,
                    Microphone.name == name,
                    Microphone.id != microphone_id).first()
                if other_named:
                    self.set_status(400)
                    await self.finish({'message': 'Name already taken'})
                    return

                description: str = data.get('description', None)

                microphone.name = name
                microphone.description = description
                session.commit()

                self.set_status(200)
                await self.finish({'message': 'Successfully updated microphone'})

                await self.application.ws_send_to_all('NOOP', 'GET_MICROPHONE_LIST', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show: Show = session.query(Show).get(show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                microphone_id = data.get('id', None)
                if not microphone_id:
                    self.set_status(400)
                    await self.finish({'message': 'ID missing'})
                    return

                entry: Microphone = session.get(Microphone, microphone_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully deleted microphone'})

                    await self.application.ws_send_to_all('NOOP', 'GET_MICROPHONE_LIST', {})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 microphone not found'})
            else:
                self.set_status(404)
                await self.finish({'message': '404 microphone not found'})
