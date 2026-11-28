from sqlalchemy import select

from models.script import Script
from models.session import Session
from models.show import Show
from models.user import User
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import requires_show


def _session_summaries(session, client_sessions) -> list[dict]:
    """Summarise client sessions as ``{internal_id, username}`` dicts."""
    summaries = []
    for client_session in client_sessions:
        user = (
            session.get(User, client_session.user_id)
            if client_session.user_id
            else None
        )
        summaries.append(
            {
                "internal_id": client_session.internal_id,
                "username": user.username if user else None,
            }
        )
    return summaries


@ApiRoute("show/script/config", ApiVersion.V1)
class ScriptStatusController(BaseAPIController):
    async def _has_unsaved_draft(self, session) -> bool:
        """True if the current show's script has an unsaved collaborative draft."""
        current_show = self.get_current_show()
        if not current_show:
            return False
        show = session.get(Show, current_show["id"])
        if not show:
            return False
        script = session.scalar(select(Script).where(Script.show_id == show.id))
        if not (script and script.current_revision):
            return False
        room_manager = getattr(self.application, "room_manager", None)
        if not room_manager:
            return False
        return await room_manager.has_unsaved_changes()

    @requires_show
    async def get(self):
        with self.make_session() as session:
            editors = _session_summaries(
                session, session.scalars(select(Session).where(Session.is_editor)).all()
            )
            cutters = _session_summaries(
                session,
                session.scalars(select(Session).where(Session.is_cutting)).all(),
            )
            has_draft = await self._has_unsaved_draft(session)

            data = {
                "editors": editors,
                "cutters": cutters,
                "hasDraft": has_draft,
                # Backward-compatible fields for the current client single-editor
                # UI (stores/scriptConfig.ts), which doesn't yet understand the
                # collab `editors`/`cutters` model. Remove once client is
                # migrated onto the new shape (see plans/COLLABORATIVE_EDITING_V3_PLAN.md).
                "canRequestEdit": len(editors) == 0,
                "currentEditor": editors[0]["internal_id"] if editors else None,
            }

            self.set_status(200)
            self.finish(data)
