from tornado import escape

from controllers.base_controller import BaseAPIController
from models.models import Show, Act
from models.schemas import ActSchema
from utils.route import ApiRoute, ApiVersion


@ApiRoute('show/act', ApiVersion.v1)
class ActController(BaseAPIController):

    def get(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']
        act_schema = ActSchema()

        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    acts = [act_schema.dump(c) for c in show.act_list]
                    self.set_status(200)
                    self.finish({'acts': acts})
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

                    session.add(Act(show_id=show.id, name=name, interval_after=interval_after))
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully added act'})

                    await self.application.ws_send_to_all('NOOP', 'GET_ACT_LIST', {})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})

    async def patch(self):
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
                        entry.first_name = name

                        interval_after: bool = data.get('interval_after', None)
                        if interval_after is None:
                            self.set_status(400)
                            await self.finish({'message': 'Interval after missing'})
                            return
                        entry.interval_after = interval_after

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
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})

    async def delete(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            await self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']
        if show_id:
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
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})
