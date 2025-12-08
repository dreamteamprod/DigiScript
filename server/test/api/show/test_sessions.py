import tornado.escape

from models.session import ShowSession
from models.show import Show
from test.utils import DigiScriptTestCase


class TestSessionsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/sessions endpoint."""

    def setUp(self):
        super().setUp()
        # Create a test show
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_sessions_empty(self):
        """Test GET /api/v1/show/sessions with no sessions.

        This tests the query at line 26-29 in controllers/api/show/sessions.py:
        session.query(ShowSession).filter(ShowSession.show_id == show.id).all()
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
            show_session1 = ShowSession(show_id=self.show_id, user_id=None)
            show_session2 = ShowSession(show_id=self.show_id, user_id=None)
            session.add(show_session1)
            session.add(show_session2)
            session.commit()

        response = self.fetch("/api/v1/show/sessions")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["sessions"]))
