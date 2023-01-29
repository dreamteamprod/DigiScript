import os

from tornado.testing import AsyncHTTPTestCase

from digi_server.app_server import DigiScriptServer


class DigiScriptTestCase(AsyncHTTPTestCase):

    def get_app(self):
        base_path = os.path.join(os.path.dirname(__file__), 'conf')
        settings_path = os.path.join(base_path, 'digiscript.json')
        self.settings_path = settings_path
        return DigiScriptServer(settings_path=settings_path)

    def tearDown(self):
        super().tearDown()
        os.remove(self.settings_path)
