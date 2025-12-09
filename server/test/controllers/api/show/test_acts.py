import tornado.escape

from models.show import Act, Show
from test.conftest import DigiScriptTestCase


class TestActController(DigiScriptTestCase):
    """Test suite for /api/v1/show/act endpoint."""

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

    def test_get_acts_empty(self):
        """Test GET /api/v1/show/act with no acts.

        This tests the query at line 25-26 in acts.py:
        session.scalars(select(Act).where(Act.show_id == show.id)).all()
        """
        response = self.fetch("/api/v1/show/act")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("acts", response_body)
        self.assertEqual([], response_body["acts"])

    def test_get_acts_with_data(self):
        """Test GET /api/v1/show/act with existing acts."""
        # Create test acts
        with self._app.get_db().sessionmaker() as session:
            act1 = Act(show_id=self.show_id, name="Act 1", interval_after=False)
            act2 = Act(
                show_id=self.show_id,
                name="Act 2",
                interval_after=True,
                previous_act_id=None,
            )
            session.add(act1)
            session.add(act2)
            session.commit()

        response = self.fetch("/api/v1/show/act")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["acts"]))
        act_names = [act["name"] for act in response_body["acts"]]
        self.assertIn("Act 1", act_names)
        self.assertIn("Act 2", act_names)
