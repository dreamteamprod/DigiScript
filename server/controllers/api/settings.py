from tornado import escape

from utils.web.base_controller import BaseAPIController
from digi_server.logger import get_logger
from utils.web.route import ApiRoute, ApiVersion
from digi_server.settings import Settings
from utils.web.web_decorators import no_live_session


@ApiRoute('settings', ApiVersion.v1)
class SettingsController(BaseAPIController):
    async def get(self):
        settings: Settings = self.application.digi_settings
        settings_json = await settings.as_json()
        await self.finish(settings_json)

    @no_live_session
    async def patch(self):
        settings: Settings = self.application.digi_settings

        data = escape.json_decode(self.request.body)
        get_logger().debug(f'New settings data patched: {data}')

        for k, v in data.items():
            await settings.set(k, v)

        settings_json = await settings.as_json()
        await self.application.ws_send_to_all(
            'SETTINGS_CHANGED',
            'WS_SETTINGS_CHANGED',
            settings_json)

        self.set_status(200)
        self.write({'message': 'Settings updated'})


@ApiRoute('settings/raw', ApiVersion.v1)
class RawSettingsController(BaseAPIController):
    async def get(self):
        settings: Settings = self.application.digi_settings
        settings_json = await settings.raw_json()
        await self.finish(settings_json)
