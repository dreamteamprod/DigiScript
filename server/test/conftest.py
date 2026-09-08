import json
import logging
import os

from sqlalchemy import inspect
from tornado import escape
from tornado.testing import AsyncHTTPTestCase

from digi_server.app_server import DigiScriptServer
from digi_server.logger import add_logging_level
from models import models


# main.py registers the TRACE level for the real app process; tests bootstrap
# DigiScriptServer directly and never import main.py, so register it here too —
# otherwise any get_logger().trace(...) call raises AttributeError under test.
if not hasattr(logging, "TRACE"):
    add_logging_level("TRACE", logging.DEBUG - 5)


class DigiScriptTestCase(AsyncHTTPTestCase):
    def get_app(self):
        return DigiScriptServer(
            port=0,  # Let OS assign a free port for testing
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

    def _create_and_login_admin(self, username="admin", password="adminpass"):
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": username, "password": password, "is_admin": True}
            ),
        )
        resp = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": username, "password": password}),
        )
        return escape.json_decode(resp.body)["access_token"]

    def _create_and_login_user(self, admin_token, username="user", password="userpass"):
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": username, "password": password, "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": username, "password": password}),
        )
        return escape.json_decode(resp.body)["access_token"]
