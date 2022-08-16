from tornado import escape

from models.models import Show, Scene
from models.schemas import SceneSchema
from utils.base_controller import BaseAPIController
from utils.route import ApiRoute, ApiVersion


@ApiRoute('show/scene', ApiVersion.v1)
class SceneController(BaseAPIController):

    def get(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']
        scene_schema = SceneSchema()

        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    scenes = [scene_schema.dump(c) for c in show.scene_list]
                    self.set_status(200)
                    self.finish({'scenes': scenes})
                else:
                    self.set_status(404)
                    self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            self.write({'message': '404 show not found'})

    async def post(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            await self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    act_id: int = data.get('act_id', None)
                    if not act_id:
                        self.set_status(400)
                        await self.finish({'message': 'Act ID missing'})
                        return

                    name: str = data.get('name', None)
                    if not name:
                        self.set_status(400)
                        await self.finish({'message': 'Name missing'})
                        return

                    next_scene_id = data.get('next_scene', None)

                    new_scene = Scene(
                        show_id=show_id,
                        act_id=act_id,
                        name=name,
                        next_scene_id=next_scene_id)
                    session.add(new_scene)

                    previous_scene_id = data.get('previous_scene_id', None)

                    if previous_scene_id:
                        previous_scene: Scene = session.query(Scene).get(previous_scene_id)
                        if not previous_scene:
                            self.set_status(404)
                            await self.finish({'message': 'Previous scene not found'})
                            return
                        session.flush()
                        previous_scene.next_scene_id = new_scene.id

                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully added scene'})

                    await self.application.ws_send_to_all('NOOP', 'GET_SCENE_LIST', {})

                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})
