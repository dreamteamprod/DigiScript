import tornado.escape

from models.script import Script, ScriptRevision
from models.show import Show
from .test_utils import DigiScriptTestCase


class TestScriptRevisionsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/revisions endpoints."""

    def setUp(self):
        super().setUp()
        # Create base test data
        with self._app.get_db().sessionmaker() as session:
            # Create a test show
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create script
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            # Create first revision
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id

            # Link revision to script
            script.current_revision = revision1.id

            # Create second revision
            revision2 = ScriptRevision(
                script_id=script.id,
                revision=2,
                description="Second",
                previous_revision_id=revision1.id,
            )
            session.add(revision2)
            session.flush()
            self.revision2_id = revision2.id

            session.commit()

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_revisions(self):
        """Test GET /api/v1/show/script/revisions.

        This tests the query at line 36:
        session.query(Script).filter(Script.show_id == show.id).first()
        """
        response = self.fetch("/api/v1/show/script/revisions")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(self.revision1_id, response_body["current_revision"])
        self.assertEqual(2, len(response_body["revisions"]))

    def test_get_revisions_no_script(self):
        """Test GET /api/v1/show/script/revisions returns 404 when no script exists."""
        # Create a show with no script
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Empty Show")
            session.add(show2)
            session.commit()
            empty_show_id = show2.id

        self._app.digi_settings.settings["current_show"].set_value(empty_show_id)

        response = self.fetch("/api/v1/show/script/revisions")
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("404 script not found", response_body["message"])


class TestScriptCurrentRevisionController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/revisions/current endpoints."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_current_revision(self):
        """Test GET /api/v1/show/script/revisions/current.

        This tests the query at line 255:
        session.query(Script).filter(Script.show_id == show.id).first()
        """
        response = self.fetch("/api/v1/show/script/revisions/current")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(self.revision_id, response_body["current_revision"])

    def test_get_current_revision_no_script(self):
        """Test GET returns 404 when no script exists."""
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Empty Show")
            session.add(show2)
            session.commit()
            empty_show_id = show2.id

        self._app.digi_settings.settings["current_show"].set_value(empty_show_id)

        response = self.fetch("/api/v1/show/script/revisions/current")
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("404 script not found", response_body["message"])
