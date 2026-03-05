from sqlalchemy import select

from models.script import Script
from models.session import Session
from models.show import Show
from models.user import User
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import requires_show


@ApiRoute("show/script/config", ApiVersion.V1)
class ScriptStatusController(BaseAPIController):
    @requires_show
    async def get(self):
        with self.make_session() as session:
            # Editors
            editor_sessions = session.scalars(
                select(Session).where(Session.is_editor)
            ).all()
            editors = []
            for es in editor_sessions:
                user = session.get(User, es.user_id) if es.user_id else None
                editors.append(
                    {
                        "internal_id": es.internal_id,
                        "username": user.username if user else None,
                    }
                )

            # Cutters
            cutter_sessions = session.scalars(
                select(Session).where(Session.is_cutting)
            ).all()
            cutters = []
            for cs in cutter_sessions:
                user = session.get(User, cs.user_id) if cs.user_id else None
                cutters.append(
                    {
                        "internal_id": cs.internal_id,
                        "username": user.username if user else None,
                    }
                )

            # Check for unsaved draft
            has_draft = False
            current_show = self.get_current_show()
            if current_show:
                show = session.get(Show, current_show["id"])
                if show:
                    script = session.scalar(
                        select(Script).where(Script.show_id == show.id)
                    )
                    if script and script.current_revision:
                        room_manager = getattr(self.application, "room_manager", None)
                        if room_manager:
                            has_draft = await room_manager.has_unsaved_changes()

            data = {
                "editors": editors,
                "cutters": cutters,
                "hasDraft": has_draft,
            }

            self.set_status(200)
            self.finish(data)
