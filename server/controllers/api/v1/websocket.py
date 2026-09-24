from sqlalchemy import select

from models.session import Session
from schemas.schemas import SessionSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import require_admin


@ApiRoute("ws/sessions", ApiVersion.V1, ignore_logging=True)
class WebsocketSessionsController(BaseAPIController):
    @require_admin
    def get(self):
        """List connected WebSocket sessions (admin only).

        The only callers are the admin-only System config pages of both clients,
        which show each session's uuid. Uuids are enough to resume a session over
        REFRESH_CLIENT, so this list is not public.
        """
        session_scheme = SessionSchema()
        with self.make_session() as session:
            sessions = session.scalars(select(Session)).all()
            sessions = [session_scheme.dump(s) for s in sessions]

        self.set_status(200)
        self.write({"sessions": sessions})
