import tornado.escape
from sqlalchemy import select

from models.mics import Microphone
from models.show import Show
from test.conftest import DigiScriptTestCase


class TestMicrophoneController(DigiScriptTestCase):
    """Test suite for /api/v1/show/microphones endpoint."""

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

    def test_get_microphones_empty(self):
        """Test GET /api/v1/show/microphones with no microphones.

        This tests the query at line 25-28 in controllers/api/show/microphones.py:
        session.scalars(select(Microphone).where(Microphone.show_id == show.id)).all()
        """
        response = self.fetch("/api/v1/show/microphones")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("microphones", response_body)
        self.assertEqual([], response_body["microphones"])

    def test_get_microphones_with_data(self):
        """Test GET /api/v1/show/microphones with existing microphones."""
        # Create test microphones
        with self._app.get_db().sessionmaker() as session:
            mic1 = Microphone(show_id=self.show_id, name="Mic 1", description="Test")
            mic2 = Microphone(show_id=self.show_id, name="Mic 2", description="Test")
            session.add(mic1)
            session.add(mic2)
            session.commit()

        response = self.fetch("/api/v1/show/microphones")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["microphones"]))
        mic_names = [m["name"] for m in response_body["microphones"]]
        self.assertIn("Mic 1", mic_names)
        self.assertIn("Mic 2", mic_names)


class TestMicrophoneAllocationsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/microphones/allocations endpoint."""

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

    def test_get_allocations_empty(self):
        """Test GET /api/v1/show/microphones/allocations with no microphones.

        This tests the query at line 192-195 in microphones.py:
        session.scalars(select(Microphone).where(Microphone.show_id == show.id)).all()
        """
        response = self.fetch("/api/v1/show/microphones/allocations")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("allocations", response_body)
        self.assertEqual({}, response_body["allocations"])

    def test_get_allocations_with_microphones(self):
        """Test GET allocations with existing microphones."""
        # Create test microphones
        with self._app.get_db().sessionmaker() as session:
            mic = Microphone(show_id=self.show_id, name="Mic 1", description="Test")
            session.add(mic)
            session.flush()
            mic_id = mic.id
            session.commit()

        response = self.fetch("/api/v1/show/microphones/allocations")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn(str(mic_id), response_body["allocations"])
