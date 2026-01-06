from sqlalchemy import select
from tornado import escape

from models.session import SessionTag, ShowSession
from models.show import Show
from rbac.role import Role
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/sessions/assign-tags", ApiVersion.V1)
class SessionTagAssignmentController(BaseAPIController):
    @requires_show
    @no_live_session
    async def patch(self):
        """
        Assign tags to a session (replaces all existing tags).

        Request body:
            session_id (int): ID of the session to update
            tag_ids (list[int]): Complete list of tag IDs to assign (can be empty)

        Returns:
            200: Successfully updated session tags
            400: Invalid request (missing/invalid fields)
            403: Insufficient permissions
            404: Session or show not found
        """
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
                return

            self.requires_role(show, Role.WRITE)
            data = escape.json_decode(self.request.body)

            # Validate session_id
            session_id = data.get("session_id", None)
            if session_id is None:
                self.set_status(400)
                await self.finish({"message": "session_id missing"})
                return
            if not isinstance(session_id, int):
                self.set_status(400)
                await self.finish({"message": "session_id must be an integer"})
                return

            # Validate tag_ids
            tag_ids = data.get("tag_ids", None)
            if tag_ids is None:
                self.set_status(400)
                await self.finish({"message": "tag_ids missing"})
                return

            if not isinstance(tag_ids, list):
                self.set_status(400)
                await self.finish({"message": "tag_ids must be a list"})
                return

            # Fetch session and verify it belongs to current show
            show_session = session.get(ShowSession, session_id)
            if not show_session:
                self.set_status(404)
                await self.finish({"message": "404 session not found"})
                return
            if show_session.show_id != show_id:
                self.set_status(403)
                await self.finish(
                    {"message": "Session does not belong to current show"}
                )
                return

            # If empty list, clear all tags
            if len(tag_ids) == 0:
                show_session.tags = []
                session.commit()
                self.set_status(200)
                await self.finish({"message": "Successfully updated session tags"})
                await self.application.ws_send_to_all(
                    "NOOP", "GET_SHOW_SESSION_DATA", {}
                )
                return

            # Fetch all tags and verify they exist and belong to the show
            tags = session.scalars(
                select(SessionTag).where(
                    SessionTag.id.in_(tag_ids), SessionTag.show_id == show_id
                )
            ).all()

            # Verify all tag_ids were valid
            if len(tags) != len(tag_ids):
                self.set_status(400)
                await self.finish({"message": "One or more tag IDs are invalid"})
                return

            # Assign tags to session, commit, and notify clients
            show_session.tags = tags
            session.commit()
            self.set_status(200)
            await self.finish({"message": "Successfully updated session tags"})
            await self.application.ws_send_to_all("NOOP", "GET_SHOW_SESSION_DATA", {})
