import tornado.escape

from models.script import Script, ScriptRevision
from models.show import Character, Show
from test.utils import DigiScriptTestCase


class TestCharacterStatsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/character/stats endpoint."""

    def setUp(self):
        super().setUp()
        # Create a test show with script
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_character_stats(self):
        """Test GET /api/v1/show/character/stats.

        This tests the query at line 183-184 in characters.py:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/character/stats")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("line_counts", response_body)

    def test_get_character_stats_no_script(self):
        """Test GET returns error when no script exists."""
        # Create a show without a script
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Show 2")
            session.add(show2)
            session.flush()
            show2_id = show2.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show2_id)

        response = self.fetch("/api/v1/show/character/stats")
        # Should get an error because there's no script
        self.assertNotEqual(200, response.code)
