import tornado.escape

from models.script import Script, ScriptRevision
from models.show import Show, ShowScriptType
from test.conftest import DigiScriptTestCase


class TestShowsController(DigiScriptTestCase):
    """Test suite for /api/v1/shows endpoint."""

    def setUp(self):
        super().setUp()
        # Create admin user and token for authenticated requests
        with self._app.get_db().sessionmaker() as session:
            from models.user import User

            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            user_id = admin.id
            session.commit()

        self.token = self._app.jwt_service.create_access_token({"user_id": user_id})

    def test_get_shows_empty(self):
        """Test GET /api/v1/shows with no shows.

        This tests the query at line 214 in shows.py:
        session.scalars(select(Show)).all()
        """
        response = self.fetch("/api/v1/shows")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("shows", response_body)
        self.assertEqual([], response_body["shows"])

    def test_get_shows_with_data(self):
        """Test GET /api/v1/shows with existing shows."""
        # Create test shows
        with self._app.get_db().sessionmaker() as session:
            show1 = Show(name="Show 1", script_mode=ShowScriptType.FULL)
            show2 = Show(name="Show 2", script_mode=ShowScriptType.FULL)
            session.add(show1)
            session.add(show2)
            session.flush()

            # Add scripts for each show
            script1 = Script(show_id=show1.id)
            script2 = Script(show_id=show2.id)
            session.add(script1)
            session.add(script2)
            session.flush()

            revision1 = ScriptRevision(
                script_id=script1.id, revision=1, description="Initial"
            )
            revision2 = ScriptRevision(
                script_id=script2.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.add(revision2)
            session.flush()

            script1.current_revision = revision1.id
            script2.current_revision = revision2.id
            session.commit()

        response = self.fetch("/api/v1/shows")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["shows"]))
        self.assertEqual("Show 1", response_body["shows"][0]["name"])
        self.assertEqual("Show 2", response_body["shows"][1]["name"])

    def test_create_show_with_script_mode(self):
        """Test POST /api/v1/show with script_mode."""
        response = self.fetch(
            "/api/v1/show",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "name": "Test Show",
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                    "script_mode": ShowScriptType.FULL.value,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify in database
        with self._app.get_db().sessionmaker() as session:
            from sqlalchemy import select

            show = session.scalar(select(Show).where(Show.name == "Test Show"))
            self.assertIsNotNone(show)
            self.assertEqual(ShowScriptType.FULL, show.script_mode)

    def test_create_show_missing_script_mode(self):
        """Test POST /api/v1/show fails without script_mode."""
        response = self.fetch(
            "/api/v1/show",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "name": "Test Show",
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                    # script_mode intentionally missing
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Script mode missing", response_body["message"])

    def test_create_show_invalid_script_mode(self):
        """Test POST /api/v1/show fails with invalid script_mode."""
        response = self.fetch(
            "/api/v1/show",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "name": "Test Show",
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                    "script_mode": 999,  # Invalid value
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid script mode value", response_body["message"])
