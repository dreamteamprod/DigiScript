import json
import os

from tornado.testing import AsyncHTTPTestCase

from digi_server.app_server import DigiScriptServer


class DigiScriptTestCase(AsyncHTTPTestCase):

    def get_app(self):
        return DigiScriptServer(settings_path=self.settings_path)

    def setUp(self):
        base_path = os.path.join(os.path.dirname(__file__), 'conf')
        settings_path = os.path.join(base_path, 'digiscript.json')
        self.settings_path = settings_path

        if not os.path.exists(os.path.dirname(self.settings_path)):
            os.makedirs(os.path.dirname(self.settings_path))

        with open(self.settings_path, 'w', encoding='UTF-8') as file_pointer:
            json.dump({
                'db_path': 'sqlite://'
            }, file_pointer)

        super().setUp()

    def tearDown(self):
        super().tearDown()
        os.remove(self.settings_path)
