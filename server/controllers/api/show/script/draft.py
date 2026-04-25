from sqlalchemy import select

from controllers.api.constants import ERROR_SCRIPT_NOT_FOUND, ERROR_SHOW_NOT_FOUND
from models.script import Script
from models.show import Show
from rbac.role import Role
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import requires_show


@ApiRoute("show/script/draft", ApiVersion.V1)
class ScriptDraftController(BaseAPIController):
    @requires_show
    async def delete(self):
        """Discard the current script draft.

        Deletes the draft file and DB record, then closes the room so all
        connected clients receive ROOM_CLOSED and revert to the saved
        script.
        """
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return

            script = session.scalars(
                select(Script).where(Script.show_id == show.id)
            ).first()
            if not script:
                self.set_status(404)
                await self.finish({"message": ERROR_SCRIPT_NOT_FOUND})
                return

            self.requires_role(script, Role.WRITE)

        room_manager = getattr(self.application, "room_manager", None)
        if room_manager:
            await room_manager.discard_active_room()

        await self.application.ws_send_to_all("NOOP", "GET_SCRIPT_CONFIG_STATUS", {})
        await self.application.ws_send_to_all("NOOP", "GET_SCRIPT_REVISIONS", {})

        self.set_status(200)
        await self.finish({"message": "Draft discarded"})
