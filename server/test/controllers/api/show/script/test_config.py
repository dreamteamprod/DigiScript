import tornado.escape

from models.script import Script, ScriptRevision
from models.script_draft import ScriptDraft
from models.session import Session
from models.show import Show, ShowScriptType
from models.user import User
from test.conftest import DigiScriptTestCase


class TestScriptStatusController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/config endpoint."""

    def setUp(self):
        super().setUp()
        # Create show + script + revision (needed for @requires_show)
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Rev"
            )
            session.add(revision)
            session.flush()
            script.current_revision = revision.id
            self.revision_id = revision.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_script_config_no_editors(self):
        """GET with no editors returns empty lists and hasDraft=false."""
        response = self.fetch("/api/v1/show/script/config")
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertEqual([], body["editors"])
        self.assertEqual([], body["cutters"])
        self.assertFalse(body["hasDraft"])

    def test_get_script_config_with_editor(self):
        """GET with an editor session returns editor in list."""
        with self._app.get_db().sessionmaker() as session:
            user = User(username="alice", password="hashed")
            session.add(user)
            session.flush()
            user_id = user.id

            editor_session = Session(
                internal_id="editor123",
                user_id=user_id,
                is_editor=True,
            )
            session.add(editor_session)
            session.commit()

        response = self.fetch("/api/v1/show/script/config")
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertEqual(1, len(body["editors"]))
        self.assertEqual("editor123", body["editors"][0]["internal_id"])
        self.assertEqual("alice", body["editors"][0]["username"])
        self.assertEqual([], body["cutters"])

    def test_get_script_config_with_cutter(self):
        """GET with a cutter session returns cutter in list."""
        with self._app.get_db().sessionmaker() as session:
            user = User(username="bob", password="hashed")
            session.add(user)
            session.flush()
            user_id = user.id

            cutter_session = Session(
                internal_id="cutter456",
                user_id=user_id,
                is_cutting=True,
            )
            session.add(cutter_session)
            session.commit()

        response = self.fetch("/api/v1/show/script/config")
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertEqual([], body["editors"])
        self.assertEqual(1, len(body["cutters"]))
        self.assertEqual("cutter456", body["cutters"][0]["internal_id"])
        self.assertEqual("bob", body["cutters"][0]["username"])

    def test_get_script_config_with_draft(self):
        """GET returns hasDraft=true when ScriptDraft exists."""
        with self._app.get_db().sessionmaker() as session:
            draft = ScriptDraft(revision_id=self.revision_id, data_path="/tmp/test.yjs")
            session.add(draft)
            session.commit()

        response = self.fetch("/api/v1/show/script/config")
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertTrue(body["hasDraft"])

    def test_get_script_config_no_show_returns_400(self):
        """GET returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)

        response = self.fetch("/api/v1/show/script/config")
        self.assertEqual(400, response.code)
