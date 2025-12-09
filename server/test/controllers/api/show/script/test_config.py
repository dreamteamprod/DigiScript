import tornado.escape
from sqlalchemy import select

from models.session import Session
from test.conftest import DigiScriptTestCase


class TestScriptStatusController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/config endpoint."""

    def test_get_script_config_no_editors(self):
        """Test GET /api/v1/show/script/config with no editors.

        This tests the query at line 13:
        session.scalars(select(Session).where(Session.is_editor)).all()
        """
        response = self.fetch("/api/v1/show/script/config")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertTrue(response_body["canRequestEdit"])
        self.assertIsNone(response_body["currentEditor"])

    def test_get_script_config_with_editor(self):
        """Test GET /api/v1/show/script/config with an editor session."""
        # Create an editor session
        with self._app.get_db().sessionmaker() as session:
            editor_session = Session(internal_id="editor123", is_editor=True)
            session.add(editor_session)
            session.commit()

        response = self.fetch("/api/v1/show/script/config")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertFalse(response_body["canRequestEdit"])
        self.assertEqual("editor123", response_body["currentEditor"])
