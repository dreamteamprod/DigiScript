from datetime import UTC, datetime
from typing import List

from sqlalchemy import select
from tornado import escape

from controllers.api.constants import ERROR_SHOW_NOT_FOUND
from models.script import Script
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
                self.finish({"message": ERROR_SHOW_NOT_FOUND})


@ApiRoute("show/sessions/start", ApiVersion.V1)
class SessionStartController(BaseAPIController):
    def _start_problem(self, session, show: Show, data: dict):
        """Check a start request, returning ``(status, message)`` if it is refused.

        ``session_id`` comes from the request body and client uuids are not
        secret, so only the requester's own client may lead the show.

        :param session: Active SQLAlchemy session.
        :param show: The current show.
        :param data: The decoded request body.
        :returns: ``(status, message)`` on a problem, else ``(None, (client, script))``.
        """
        if show.current_session_id:
            return 409, "409 session already active"
        session_id = data.get("session_id", None)
        if not session_id:
            return 400, "session_id missing"
        user_session: Session = session.get(Session, session_id)
        if not user_session:
            return 400, "Unable to find session given session_id"
        if user_session.user_id != self.current_user["id"]:
            return 403, "session_id is not a client of this user"
        scripts: List[Script] = session.scalars(
            select(Script).where(Script.show_id == show.id)
        ).all()
        if len(scripts) != 1:
            return 400, "Unable to start show session without a script"
        return None, (user_session, scripts[0])

    @requires_show
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return
            self.requires_role(show, Role.EXECUTE)
            data = escape.json_decode(self.request.body)
            status, result = self._start_problem(session, show, data)
            if status is not None:
                self.set_status(status)
                await self.finish({"message": result})
                return
            user_session, script = result

            show_session = ShowSession(
                show_id=show_id,
                script_revision_id=script.current_revision,
                start_date_time=datetime.now(UTC),
                end_date_time=None,
                client_internal_id=user_session.internal_id,
                # The requester, who owns user_session (checked above).
                user_id=self.current_user["id"],
            )
            session.add(show_session)
            session.flush()

            show.current_session_id = show_session.id
            session.commit()

            self.set_status(200)
            self.write({"message": "Successfully started show session"})

            await self.application.ws_send_to_all("NOOP", "GET_SHOW_SESSION_DATA", {})
            await self.application.ws_send_to_all("START_SHOW", "NOOP", {})


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
                    show_session.end_date_time = datetime.now(UTC)
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
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
