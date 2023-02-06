from models.session import Session
from schemas.schemas import SessionSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion


@ApiRoute('ws/sessions', ApiVersion.V1)
class WebsocketSessionsController(BaseAPIController):

    def get(self):
        session_scheme = SessionSchema()
        with self.make_session() as session:
            sessions = session.query(Session).all()
            sessions = [session_scheme.dump(s) for s in sessions]

        self.set_status(200)
        self.write({'sessions': sessions})
