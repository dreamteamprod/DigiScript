import ast
from pathlib import Path

import tornado.escape
from sqlalchemy import func, select
from tornado.testing import gen_test

from models.session import Session
from models.settings import SystemSettings
from models.user import User
from test.conftest import DigiScriptTestCase
from utils.web.request_size_metrics import http_request_body_bytes


class TestDigiScriptServer(DigiScriptTestCase):
    def test_debug(self):
        response = self.fetch("/debug")
        response_body = tornado.escape.json_decode(response.body)

        self.assertEqual(200, response.code)
        self.assertTrue("status" in response_body)
        self.assertEqual("OK", response_body["status"])

    def test_debug_mode_is_opt_in(self):
        """Debug mode must be opt-in via ``--debug``."""
        tree = ast.parse(
            (Path(__file__).parents[2] / "main.py").read_text(encoding="utf-8")
        )
        defaults = [
            kw.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "define"
            and node.args
            and getattr(node.args[0], "value", None) == "debug"
            for kw in node.keywords
            if kw.arg == "default"
        ]
        self.assertEqual([False], defaults)

    def test_traceback_not_returned_to_client(self):
        """Even with debug=True (as in the test app) no traceback is returned."""
        self.assertTrue(self._app.settings["debug"])
        self.assertFalse(self._app.settings["serve_traceback"])
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body="{not valid json",
        )
        self.assertGreaterEqual(response.code, 400)
        self.assertNotIn(b"Traceback", response.body)
        self.assertNotIn(b".py", response.body)

    def test_request_body_size_observed(self):
        """Request bodies are recorded in the size histogram, labelled by handler."""
        labels = ("ApiFallback", "POST")
        before = self._body_count(*labels)
        self.fetch("/api/v1/nonexistent", method="POST", body="x" * 2000)
        self.assertEqual(before + 1, self._body_count(*labels))

    def test_request_without_body_not_observed(self):
        """Body-less requests do not add to the size histogram."""
        before = self._body_count("ApiFallback", "GET")
        self.fetch("/api/v1/nonexistent")
        self.assertEqual(before, self._body_count("ApiFallback", "GET"))

    @staticmethod
    def _body_count(handler, method):
        for metric in http_request_body_bytes.collect():
            for sample in metric.samples:
                if (
                    sample.name.endswith("_count")
                    and sample.labels.get("handler") == handler
                    and sample.labels.get("method") == method
                ):
                    return sample.value
        return 0

    def test_api_debug(self):
        response = self.fetch("/api/v1/debug")
        response_body = tornado.escape.json_decode(response.body)

        self.assertEqual(200, response.code)
        self.assertTrue("status" in response_body)
        self.assertEqual("OK", response_body["status"])
        self.assertTrue("api_version" in response_body)
        self.assertEqual(1, response_body["api_version"])

    def test_debug_metrics(self):
        response = self.fetch("/debug/metrics")

        self.assertEqual(200, response.code)

    def test_initialization_detects_no_admin(self):
        """Test that initialization correctly detects when no admin exists.

        This tests the query at line 110:
        session.query(User).filter(User.is_admin).first()
        """
        # The server was already initialized in setUp() with no admin
        # Verify it detected the absence correctly
        has_admin = self._app.digi_settings.settings["has_admin_user"].get_value()
        self.assertFalse(has_admin)

    @gen_test
    async def test_validate_has_admin_method(self):
        """Test the _validate_has_admin() method directly.

        This tests the query at line 349:
        session.query(User).filter(User.is_admin).first()
        """
        # Initially no admin
        has_admin = self._app.digi_settings.settings["has_admin_user"].get_value()
        self.assertFalse(has_admin)

        # Create an admin user
        with self._app.get_db().sessionmaker() as session:
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.commit()

        # Call the actual method from app_server.py
        await self._app._validate_has_admin()

        # Verify it detected the admin
        has_admin = self._app.digi_settings.settings["has_admin_user"].get_value()
        self.assertTrue(has_admin)

    def test_initialization_validates_current_show(self):
        """Test that initialization validates current_show setting exists.

        This tests the query at line 119:
        session.query(Show).get(current_show)

        The initialization runs in setUp(). If current_show is invalid,
        it gets reset to default (None).
        """
        # After initialization, current_show should be None (default)
        # because no show exists
        current_show = self._app.digi_settings.settings.get("current_show").get_value()
        self.assertIsNone(current_show)

    def test_initialization_clears_sessions(self):
        """Test that initialization clears all sessions.

        This tests the query at line 150:
        session.query(Session).delete()

        The initialization runs in setUp() and clears the sessions table.
        """
        # After initialization, sessions table should be empty
        with self._app.get_db().sessionmaker() as session:
            count = session.scalar(select(func.count()).select_from(Session))
            self.assertEqual(0, count)

    def test_configure_jwt_creates_secret_if_missing(self):
        """Test that JWT service initialization creates a secret.

        This tests the query at lines 307-309:
        session.query(SystemSettings).filter(SystemSettings.key == "jwt_secret").first()

        The JWT service is configured in __init__, which should create
        a secret if one doesn't exist.
        """
        # The JWT service is already configured in setUp via __init__
        # Verify a secret was created in the database
        with self._app.get_db().sessionmaker() as session:
            jwt_secret = session.scalars(
                select(SystemSettings).where(SystemSettings.key == "jwt_secret")
            ).first()
            self.assertIsNotNone(jwt_secret)
            self.assertIsNotNone(jwt_secret.value)
            self.assertGreater(len(jwt_secret.value), 0)
