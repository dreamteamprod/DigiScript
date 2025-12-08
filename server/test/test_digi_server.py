import tornado.escape
from tornado.testing import gen_test
from sqlalchemy import func, select

from models.session import ShowSession
from models.show import Show
from models.user import User
from .utils import DigiScriptTestCase


class TestDigiScriptServer(DigiScriptTestCase):
    def test_debug(self):
        response = self.fetch("/debug")
        response_body = tornado.escape.json_decode(response.body)

        self.assertEqual(200, response.code)
        self.assertTrue("status" in response_body)
        self.assertEqual("OK", response_body["status"])

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
        from models.session import Session

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
        from models.settings import SystemSettings

        # The JWT service is already configured in setUp via __init__
        # Verify a secret was created in the database
        with self._app.get_db().sessionmaker() as session:
            jwt_secret = session.scalars(
                select(SystemSettings).where(SystemSettings.key == "jwt_secret")
            ).first()
            self.assertIsNotNone(jwt_secret)
            self.assertIsNotNone(jwt_secret.value)
            self.assertGreater(len(jwt_secret.value), 0)
