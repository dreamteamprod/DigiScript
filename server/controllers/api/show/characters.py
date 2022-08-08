from tornado import escape

from controllers.base_controller import BaseAPIController
from models.models import Character, Show, to_json
from utils.route import ApiRoute, ApiVersion


@ApiRoute('show/character', ApiVersion.v1)
class CastController(BaseAPIController):

    def get(self):
        pass

    async def post(self):
        pass

    async def patch(self):
        pass

    async def delete(self):
        pass
