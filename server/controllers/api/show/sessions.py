from models.session import ShowSession
from models.show import Show
from schemas.schemas import ShowSessionSchema
from utils.base_controller import BaseAPIController
from utils.requires import requires_show
from utils.route import ApiRoute, ApiVersion


@ApiRoute('show/sessions', ApiVersion.v1)
class SessionsController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()

        show_id = current_show['id']
        session_schema = ShowSessionSchema()

        if show_id:
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
        else:
            self.set_status(404)
            self.write({'message': '404 show not found'})
