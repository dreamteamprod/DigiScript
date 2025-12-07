import json
import os

from sqlalchemy import inspect
from tornado.testing import AsyncHTTPTestCase

from digi_server.app_server import DigiScriptServer
from models import models


class DigiScriptTestCase(AsyncHTTPTestCase):
    def get_app(self):
        return DigiScriptServer(
            debug=True,
            settings_path=self.settings_path,
            skip_migrations=True,
            skip_migrations_check=True,
        )

    def setUp(self):
        base_path = os.path.join(os.path.dirname(__file__), "conf")
        settings_path = os.path.join(base_path, "digiscript.json")
        self.settings_path = settings_path

        if not os.path.exists(os.path.dirname(self.settings_path)):
            os.makedirs(os.path.dirname(self.settings_path))

        with open(self.settings_path, "w", encoding="UTF-8") as file_pointer:
            json.dump({"db_path": "sqlite://"}, file_pointer)

        super().setUp()

    def tearDown(self):
        os.remove(self.settings_path)
        for rbac_table in self._app.rbac._rbac_db._mappings:
            table = self._app.rbac._rbac_db._mappings[rbac_table]
            table_inspect = inspect(table)
            models.db.metadata.remove(table_inspect.persist_selectable)

        # Dispose the database engine to ensure proper test isolation
        # This forces a new in-memory database for each test
        models.db.engine.dispose()

        super().tearDown()
