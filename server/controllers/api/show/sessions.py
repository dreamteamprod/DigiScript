from datetime import datetime

from sqlalchemy import select
from tornado import escape

from models.session import Interval, Session, ShowSession
from models.show import Show
from rbac.role import Role
from schemas.schemas import IntervalSchema, ShowSessionSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import requires_show


@ApiRoute("show/sessions", ApiVersion.V1)
class SessionsController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        session_schema = ShowSessionSchema()
        interval_schema = IntervalSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                sessions = session.scalars(
                    select(ShowSession).where(ShowSession.show_id == show.id)
                ).all()
                sessions = [session_schema.dump(s) for s in sessions]

                current_session = None
                current_interval = None
                if show.current_session_id:
                    current_session = session.get(ShowSession, show.current_session_id)

                    if current_session.current_interval_id:
                        current_interval = session.get(
                            Interval, current_session.current_interval_id
                        )
                        current_interval = interval_schema.dump(current_interval)

                    current_session = session_schema.dump(current_session)

                self.set_status(200)
                self.finish(
                    {
                        "sessions": sessions,
                        "current_session": current_session,
                        "current_interval": current_interval,
                    }
                )
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})


@ApiRoute("show/sessions/start", ApiVersion.V1)
class SessionStartController(BaseAPIController):
    @requires_show
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.EXECUTE)
                if show.current_session_id:
                    self.set_status(409)
                    await self.finish({"message": "409 session already active"})
                else:
                    data = escape.json_decode(self.request.body)

                    session_id = data.get("session_id", None)
                    if not session_id:
                        self.set_status(400)
                        await self.finish({"message": "session_id missing"})
                        return

                    user_session: Session = session.get(Session, session_id)
                    if not user_session:
                        self.set_status(400)
                        await self.finish(
                            {"message": "Unable to find session given session_id"}
                        )
                        return

                    show_session = ShowSession(
                        show_id=show_id,
                        start_date_time=datetime.utcnow(),
                        end_date_time=None,
                        client_internal_id=user_session.internal_id,
                        user_id=user_session.user.id,
                    )
                    session.add(show_session)
                    session.flush()

                    show.current_session_id = show_session.id
                    session.commit()

                    self.set_status(200)
                    self.write({"message": "Successfully started show session"})

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SHOW_SESSION_DATA", {}
                    )
                    await self.application.ws_send_to_all("START_SHOW", "NOOP", {})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


@ApiRoute("show/sessions/stop", ApiVersion.V1)
class SessionStopController(BaseAPIController):
    @requires_show
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.EXECUTE)
                if not show.current_session_id:
                    self.set_status(409)
                    await self.finish({"message": "409 no active session"})
                else:
                    show_session: ShowSession = session.get(
                        ShowSession, show.current_session_id
                    )
                    show_session.end_date_time = datetime.utcnow()
                    show.current_session_id = None
                    session.commit()

                    self.set_status(200)
                    self.write({"message": "Successfully stopped show session"})

                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SHOW_SESSION_DATA", {}
                    )
                    await self.application.ws_send_to_all("STOP_SHOW", "NOOP", {})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
