from controllers.base_controller import BaseAPIController
from models.models import Session, to_json
from utils.route import ApiRoute, ApiVersion


@ApiRoute('ws/sessions', ApiVersion.v1)
class WebsocketSessionsController(BaseAPIController):

    def get(self):
        with self.make_session() as session:
            sessions = session.query(Session).all()
            sessions = [to_json(s) for s in sessions]

        self.set_status(200)
        self.write({'sessions': sessions})
