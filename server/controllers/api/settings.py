from tornado import escape

from utils.base_controller import BaseAPIController
from utils.logger import get_logger
from utils.route import ApiRoute, ApiVersion
from utils.settings import Settings


@ApiRoute('settings', ApiVersion.v1)
class SettingsController(BaseAPIController):
    async def get(self):
        settings: Settings = self.application.digi_settings
        settings_json = await settings.as_json()
        await self.finish(settings_json)

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
