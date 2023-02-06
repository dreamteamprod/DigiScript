from datetime import datetime

from models.session import ShowSession
from models.show import Show
from schemas.schemas import ShowSessionSchema
from utils.web.base_controller import BaseAPIController
from utils.web.web_decorators import requires_show
from utils.web.route import ApiRoute, ApiVersion


@ApiRoute('show/sessions', ApiVersion.v1)
class SessionsController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']
        session_schema = ShowSessionSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                sessions = session.query(ShowSession).filter(
                    ShowSession.show_id == show.id).all()
                sessions = [session_schema.dump(s) for s in sessions]

                current_session = None
                if show.current_session_id:
                    current_session = session.query(ShowSession).get(show.current_session_id)
                    current_session = session_schema.dump(current_session)

                self.set_status(200)
                self.finish({'sessions': sessions, 'current_session': current_session})
            else:
                self.set_status(404)
                self.finish({'message': '404 show not found'})


@ApiRoute('show/sessions/start', ApiVersion.v1)
class SessionStartController(BaseAPIController):
    @requires_show
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                if show.current_session_id:
                    self.set_status(409)
                    await self.finish({'message': '409 session already active'})
                else:
                    show_session = ShowSession(
                        show_id=show_id,
                        start_date_time=datetime.utcnow(),
                        end_date_time=None
                    )
                    session.add(show_session)
                    session.flush()

                    show.current_session_id = show_session.id
                    session.commit()

                    self.set_status(200)
                    self.write({'message': 'Successfully started show session'})

                    await self.application.ws_send_to_all('NOOP', 'GET_SHOW_SESSION_DATA', {})
                    await self.application.ws_send_to_all('START_SHOW', 'NOOP', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})


@ApiRoute('show/sessions/stop', ApiVersion.v1)
class SessionStopController(BaseAPIController):
    @requires_show
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                if not show.current_session_id:
                    self.set_status(409)
                    await self.finish({'message': '409 no active session'})
                else:
                    show_session: ShowSession = session.query(ShowSession).get(
                        show.current_session_id)
                    show_session.end_date_time = datetime.utcnow()
                    show.current_session_id = None
                    session.commit()

                    self.set_status(200)
                    self.write({'message': 'Successfully stopped show session'})

                    await self.application.ws_send_to_all('NOOP', 'GET_SHOW_SESSION_DATA', {})
                    await self.application.ws_send_to_all('STOP_SHOW', 'NOOP', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})
