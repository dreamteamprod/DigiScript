import tornado.escape

from models.script import Script, ScriptRevision
from models.show import Show
from test.conftest import DigiScriptTestCase


class TestCueController(DigiScriptTestCase):
    """Test suite for /api/v1/show/cues endpoint."""

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

    def test_get_cues(self):
        """Test GET /api/v1/show/cues.

        This tests two queries in cues.py:
        - Line 176-177: Script lookup
          session.scalars(select(Script).where(Script.show_id == show.id)).first()
        - Line 190-193: CueAssociation filter
          session.scalars(select(CueAssociation).where(...)).all()
        """
        response = self.fetch("/api/v1/show/cues")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("cues", response_body)

    def test_get_cues_no_script(self):
        """Test GET returns error when no script exists."""
        # Create a show without a script
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Show 2")
            session.add(show2)
            session.flush()
            show2_id = show2.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show2_id)

        response = self.fetch("/api/v1/show/cues")
        # Should get an error because there's no script
        self.assertNotEqual(200, response.code)


class TestCueStatsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/cues/stats endpoint."""

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

    def test_get_cue_stats(self):
        """Test GET /api/v1/show/cues/stats.

        This tests the query at line 455-456 in cues.py:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/cues/stats")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("cue_counts", response_body)
