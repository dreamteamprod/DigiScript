from typing import List

from tornado import escape

from models.mics import Microphone, MicrophoneAllocation
from models.show import Show, Scene, Character
from rbac.role import Role
from schemas.schemas import MicrophoneSchema, MicrophoneAllocationSchema
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
                mics: List[Microphone] = session.query(Microphone).filter(
                    Microphone.show_id == show.id).all()
                mics = [mic_schema.dump(c) for c in mics]
                self.set_status(200)
                self.finish({'microphones': mics})
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


@ApiRoute('show/microphones/allocations', ApiVersion.V1)
class MicrophoneAllocationsController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']
        allocation_schema = MicrophoneAllocationSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                mics: List[Microphone] = session.query(Microphone).filter(
                    Microphone.show_id == show.id).all()

                allocations = {}
                for mic in mics:
                    allocations[mic.id] = [allocation_schema.dump(alloc) for
                                           alloc in mic.allocations]

                self.set_status(200)
                self.finish({'allocations': allocations})
            else:
                self.set_status(404)
                self.finish({'message': '404 show not found'})

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

                for microphone_id in data:
                    mic = session.query(Microphone).get(microphone_id)
                    if not mic:
                        self.set_status(404)
                        await self.finish({'message': '404 microphone not found'})
                        return

                    for scene_id in data[microphone_id]:
                        scene = session.query(Scene).get(scene_id)
                        if not scene:
                            self.set_status(404)
                            await self.finish({'message': '404 scene not found'})
                            return

                        existing_allocation: MicrophoneAllocation = session.query(
                            MicrophoneAllocation).filter(
                            MicrophoneAllocation.scene_id == scene.id,
                            MicrophoneAllocation.mic_id == mic.id).first()

                        character_id = data[microphone_id][scene_id]
                        if character_id:
                            character = session.query(Character).get(character_id)
                            if not character:
                                self.set_status(404)
                                await self.finish({'message': '404 character not found'})
                                return

                            if existing_allocation:
                                existing_allocation.character_id = character.id
                            else:
                                session.add(MicrophoneAllocation(
                                    mic_id=mic.id,
                                    scene_id=scene.id,
                                    character_id=character.id)
                                )
                        elif existing_allocation:
                            session.delete(existing_allocation)

                        session.flush()
                await self.application.ws_send_to_all('NOOP', 'GET_MIC_ALLOCATIONS', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})
