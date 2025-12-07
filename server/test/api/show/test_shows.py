import tornado.escape

from models.script import Script, ScriptRevision
from models.show import Show
from test.utils import DigiScriptTestCase


class TestShowsController(DigiScriptTestCase):
    """Test suite for /api/v1/shows endpoint."""

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
            show1 = Show(name="Show 1")
            show2 = Show(name="Show 2")
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
