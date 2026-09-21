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
        if data[COLLAB_SETTING] == settings.get_sync(COLLAB_SETTING):
            return False

        room_manager = self.application.room_manager
        # Every await comes first: the checks below then run with no yield between
        # them and the caller's `settings.set`, so nobody can start editing in the gap.
        unsaved = await room_manager.has_unsaved_changes()
        room = room_manager.get_active_room()
        if unsaved or (room is not None and not room.is_empty):
            return True

        with self.make_session() as session:
            busy = session.scalars(
                select(Session).where(Session.is_editor | Session.is_cutting)
            ).first()
        return busy is not None

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

        if COLLAB_SETTING in data and not isinstance(data[COLLAB_SETTING], bool):
            self.set_status(400)
            self.write({"message": f"{COLLAB_SETTING} must be a boolean"})
            return

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
