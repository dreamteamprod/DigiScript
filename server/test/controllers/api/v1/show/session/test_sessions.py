import tornado.escape

from models.script import Script, ScriptRevision
from models.session import ShowSession
from models.show import Show, ShowScriptType
from test.conftest import DigiScriptTestCase


class TestSessionsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/sessions endpoint."""

    def setUp(self):
        super().setUp()
        # Create a test show
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Revision"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_sessions_empty(self):
        """Test GET /api/v1/show/sessions with no sessions.

        This tests the query at line 26-29 in controllers/api/show/sessions.py:
        session.scalars(select(ShowSession).where(ShowSession.show_id == show.id)).all()
        """
        response = self.fetch("/api/v1/show/sessions")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("sessions", response_body)
        self.assertEqual([], response_body["sessions"])

    def test_get_sessions_with_data(self):
        """Test GET /api/v1/show/sessions with existing sessions."""
        # Create test show sessions
        with self._app.get_db().sessionmaker() as session:
            show_session1 = ShowSession(
                show_id=self.show_id,
                script_revision_id=self.revision_id,
                user_id=None,
            )
            show_session2 = ShowSession(
                show_id=self.show_id,
                script_revision_id=self.revision_id,
                user_id=None,
            )
            session.add(show_session1)
            session.add(show_session2)
            session.commit()

        response = self.fetch("/api/v1/show/sessions")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["sessions"]))

    def test_start_session_invalid_json_returns_400(self):
        """A malformed body reaches the JSON helper (a show is loaded) and gets 400."""
        token = self._create_and_login_admin()
        for body in ("nope", "[1]"):
            with self.subTest(body=body):
                response = self.fetch(
                    "/api/v1/show/sessions/start",
                    method="POST",
                    body=body,
                    headers={"Authorization": f"Bearer {token}"},
                    raise_error=False,
                )
                self.assertEqual(400, response.code)

    def test_start_session_valid_json_reaches_handler(self):
        """Control for the test above: a valid body gets the handler's own error."""
        token = self._create_and_login_admin()
        response = self.fetch(
            "/api/v1/show/sessions/start",
            method="POST",
            body="{}",
            headers={"Authorization": f"Bearer {token}"},
            raise_error=False,
        )
        self.assertEqual(400, response.code)
        self.assertEqual(
            "session_id missing", tornado.escape.json_decode(response.body)["message"]
        )
