from sqlalchemy import select
from tornado import escape

from controllers.api.constants import ERROR_COLLAB_MODE_CHANGE_BLOCKED
from digi_server.logger import get_logger
from digi_server.settings import Settings
from models.session import Session
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import (
    allow_when_password_required,
    api_authenticated,
    no_live_session,
    require_admin,
)


COLLAB_SETTING = "collaborative_script_editing"


@ApiRoute("settings", ApiVersion.V1)
class SettingsController(BaseAPIController):
    async def _collab_mode_change_blocked(self, settings: Settings, data: dict) -> bool:
        """Return True if *data* would change the editing mode while it's in use.

        Switching modes under someone would strand their work: an open classic edit
        has nowhere to go in collaborative mode, and a draft has nowhere to go in
        classic mode. Setting the same value again is always fine.

        :param settings: The application settings.
        :param data: The requested settings changes.
        :returns: True if the change must be refused.
        """
        if COLLAB_SETTING not in data:
            return False
        if bool(data[COLLAB_SETTING]) == bool(await settings.get(COLLAB_SETTING)):
            return False

        with self.make_session() as session:
            busy = session.scalars(
                select(Session).where(Session.is_editor | Session.is_cutting)
            ).first()
        if busy is not None:
            return True

        room_manager = getattr(self.application, "room_manager", None)
        if room_manager is None:
            return False
        room = room_manager.get_active_room()
        return bool(
            (room is not None and not room.is_empty)
            or await room_manager.has_unsaved_changes()
        )

    @allow_when_password_required
    async def get(self):
        settings: Settings = self.application.digi_settings
        settings_json = await settings.as_json()
        await self.finish(settings_json)

    @api_authenticated
    @require_admin
    @no_live_session
    async def patch(self):
        settings: Settings = self.application.digi_settings

        data = escape.json_decode(self.request.body)
        get_logger().debug(f"New settings data patched: {data}")

        if await self._collab_mode_change_blocked(settings, data):
            self.set_status(409)
            self.write({"message": ERROR_COLLAB_MODE_CHANGE_BLOCKED})
            return

        for k, v in data.items():
            await settings.set(k, v)

        settings_json = await settings.as_json()
        await self.application.ws_send_to_all(
            "SETTINGS_CHANGED", "WS_SETTINGS_CHANGED", settings_json
        )

        self.set_status(200)
        self.write({"message": "Settings updated"})


@ApiRoute("settings/categories", ApiVersion.V1)
class SettingsCategoriesController(BaseAPIController):
    @allow_when_password_required
    async def get(self):
        await self.finish({"categories": self.application.digi_settings.categories})


@ApiRoute("settings/raw", ApiVersion.V1)
class RawSettingsController(BaseAPIController):
    async def get(self):
        settings: Settings = self.application.digi_settings
        settings_json = await settings.raw_json()
        await self.finish(settings_json)
