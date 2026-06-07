from digi_server.settings import get_version
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion


@ApiRoute("health", ApiVersion.V1)
class HealthController(BaseAPIController):
    async def get(self):
        health_data = {"version": get_version(), "status": "ok"}
        await self.finish(health_data)
