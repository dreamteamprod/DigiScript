from settings import Settings
from controllers.base_controller import BaseController
from route import ApiRoute, ApiVersion


@ApiRoute('settings', ApiVersion.v1)
class SettingsController(BaseController):
    async def get(self):
        settings: Settings = self.application.digi_settings
        settings_json = await settings.as_json()
        await self.finish(settings_json)
