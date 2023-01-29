from tornado import escape

from models.show import Show, Act, Scene
from schemas.schemas import ActSchema
from utils.base_controller import BaseAPIController
from utils.web_decorators import requires_show, no_live_session
from utils.route import ApiRoute, ApiVersion


@ApiRoute('show/act', ApiVersion.v1)
class ActController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']
        act_schema = ActSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                acts = [act_schema.dump(c) for c in show.act_list]
                self.set_status(200)
                self.finish({'acts': acts})
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
                data = escape.json_decode(self.request.body)

                name: str = data.get('name', None)
                if not name:
                    self.set_status(400)
                    await self.finish({'message': 'Name missing'})
                    return

                interval_after: bool = data.get('interval_after', None)
                if interval_after is None:
                    self.set_status(400)
                    await self.finish({'message': 'Interval after missing'})
                    return

                previous_act_id: int = data.get('previous_act_id', None)

                new_act = Act(show_id=show.id, name=name, interval_after=interval_after,
                              previous_act_id=previous_act_id)
                session.add(new_act)
                session.flush()

                if not show.first_act:
                    show.first_act = new_act

                session.commit()

                self.set_status(200)
                await self.finish({'message': 'Successfully added act'})

                await self.application.ws_send_to_all('NOOP', 'GET_ACT_LIST', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                data = escape.json_decode(self.request.body)

                act_id = data.get('id', None)
                if not act_id:
                    self.set_status(400)
                    await self.finish({'message': 'ID missing'})
                    return

                entry: Act = session.get(Act, act_id)
                if entry:
                    name = data.get('name', None)
                    if not name:
                        self.set_status(400)
                        await self.finish({'message': 'Name missing'})
                        return
                    entry.name = name

                    interval_after: bool = data.get('interval_after', None)
                    if interval_after is None:
                        self.set_status(400)
                        await self.finish({'message': 'Interval after missing'})
                        return
                    entry.interval_after = interval_after

                    previous_act_id: int = data.get('previous_act_id', None)

                    if previous_act_id:
                        if previous_act_id == act_id:
                            self.set_status(400)
                            await self.finish({'message': 'Previous act cannot be current act'})
                            return

                        previous_act: Act = session.query(Act).get(previous_act_id)
                        if not previous_act:
                            self.set_status(400)
                            await self.finish({'message': 'Previous act not found'})
                            return

                        act_indexes = [act_id]
                        current_act: Act = previous_act
                        while current_act is not None and current_act.previous_act is not None:
                            if current_act.previous_act.id in act_indexes:
                                self.set_status(400)
                                await self.finish({
                                    'message': 'Previous act cannot form a circular '
                                               'dependency between acts'
                                })
                                return
                            current_act = current_act.previous_act

                    entry.previous_act_id = previous_act_id

                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully updated act'})

                    await self.application.ws_send_to_all('NOOP', 'GET_ACT_LIST', {})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 act not found'})
                    return
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
                data = escape.json_decode(self.request.body)

                act_id = data.get('id', None)
                if not act_id:
                    self.set_status(400)
                    await self.finish({'message': 'ID missing'})
                    return

                entry: Act = session.get(Act, act_id)
                if entry:
                    if entry.previous_act and entry.next_act:
                        entry.next_act.previous_act = entry.previous_act
                    elif entry.previous_act:
                        entry.previous_act.next_act = None
                    elif entry.next_act:
                        entry.next_act.previous_act = None

                    if show.first_act_id == entry.id:
                        show.first_act = None

                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully deleted act'})

                    await self.application.ws_send_to_all('NOOP', 'GET_ACT_LIST', {})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 act not found'})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})


@ApiRoute('show/act/first_scene', ApiVersion.v1)
class FirstSceneController(BaseAPIController):

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                data = escape.json_decode(self.request.body)

                act_id: int = data.get('act_id', None)
                if not act_id:
                    self.set_status(400)
                    await self.finish({'message': 'Act ID missing'})
                    return

                if 'scene_id' not in data:
                    self.set_status(400)
                    await self.finish({'message': 'Scene ID missing'})
                    return

                scene_id: int = data.get('scene_id', None)
                if scene_id:
                    scene: Scene = session.query(Scene).get(scene_id)
                    if not scene:
                        self.set_status(404)
                        await self.finish({'message': '404 scene not found'})
                        return
                    if scene.previous_scene_id:
                        self.set_status(400)
                        await self.finish({
                            'message': 'First scene cannot already have previous scene'
                        })
                        return

                act: Act = session.query(Act).get(act_id)
                if not act:
                    self.set_status(404)
                    await self.finish({'message': 'Act not found'})
                    return

                act.first_scene_id = scene_id
                session.commit()

                self.set_status(200)
                await self.finish({'message': 'Successfully set first scene'})

                await self.application.ws_send_to_all('NOOP', 'GET_ACT_LIST', {})

            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})
