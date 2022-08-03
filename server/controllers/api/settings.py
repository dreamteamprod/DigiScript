from tornado import escape

from controllers.ws_controller import WebSocketController
from utils.settings import Settings
from controllers.base_controller import BaseAPIController
from utils.route import ApiRoute, ApiVersion
from utils.logger import get_logger


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
        client: WebSocketController
        for client in self.application.clients:
            await client.write_message({
                'OP': 'SETTINGS_CHANGED',
                'DATA': settings_json,
                'ACTION': 'SETTINGS_CHANGED'
            })

        self.set_status(200)
        self.write({'message': 'Settings updated'})
