import tornado.escape

from models.session import Session
from test.conftest import DigiScriptTestCase


class TestWebsocketSessionsController(DigiScriptTestCase):
    """Test suite for /api/v1/ws/sessions endpoint (admin only)."""

    def _admin_headers(self):
        return {"Authorization": f"Bearer {self._create_and_login_admin()}"}

    def test_get_sessions_requires_login(self):
        """Session uuids are enough to resume a session, so the list isn't public."""
        response = self.fetch("/api/v1/ws/sessions")
        self.assertEqual(401, response.code)

    def test_get_sessions_rejects_non_admin(self):
        admin_token = self._create_and_login_admin()
        user_token = self._create_and_login_user(admin_token)
        response = self.fetch(
            "/api/v1/ws/sessions", headers={"Authorization": f"Bearer {user_token}"}
        )
        self.assertEqual(401, response.code)

    def test_get_sessions_empty(self):
        """Test GET /api/v1/ws/sessions with no sessions.

        This tests the query at line 12 in controllers/api/websocket.py:
        session.scalars(select(Session)).all()
        """
        response = self.fetch("/api/v1/ws/sessions", headers=self._admin_headers())
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("sessions", response_body)
        self.assertEqual([], response_body["sessions"])

    def test_get_sessions_with_data(self):
        """Test GET /api/v1/ws/sessions with existing sessions."""
        # Create test sessions
        with self._app.get_db().sessionmaker() as session:
            session1 = Session(internal_id="test-session-1", is_editor=False)
            session2 = Session(internal_id="test-session-2", is_editor=True)
            session.add(session1)
            session.add(session2)
            session.commit()

        response = self.fetch("/api/v1/ws/sessions", headers=self._admin_headers())
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["sessions"]))
        session_ids = [s["internal_id"] for s in response_body["sessions"]]
        self.assertIn("test-session-1", session_ids)
        self.assertIn("test-session-2", session_ids)
