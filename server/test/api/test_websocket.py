import tornado.escape

from models.session import Session
from test.utils import DigiScriptTestCase


class TestWebsocketSessionsController(DigiScriptTestCase):
    """Test suite for /api/v1/ws/sessions endpoint."""

    def test_get_sessions_empty(self):
        """Test GET /api/v1/ws/sessions with no sessions.

        This tests the query at line 12 in controllers/api/websocket.py:
        session.query(Session).all()
        """
        response = self.fetch("/api/v1/ws/sessions")
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

        response = self.fetch("/api/v1/ws/sessions")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["sessions"]))
        session_ids = [s["internal_id"] for s in response_body["sessions"]]
        self.assertIn("test-session-1", session_ids)
        self.assertIn("test-session-2", session_ids)
