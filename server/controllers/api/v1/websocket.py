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

        Uuids are not treated as secrets (``show/sessions`` and
        ``show/script/config`` expose them too): presenting one via
        REFRESH_CLIENT grants nothing, because privileges recorded against a uuid
        can only be used by a connection authenticated as its owner. This list is
        admin-only because it exposes every client's user and IP address. Its
        only callers are the admin-only System config pages of both clients.
        """
        session_scheme = SessionSchema()
        with self.make_session() as session:
            sessions = session.scalars(select(Session)).all()
            sessions = [session_scheme.dump(s) for s in sessions]

        self.set_status(200)
        self.write({"sessions": sessions})
