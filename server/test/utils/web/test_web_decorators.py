"""Tests for web_decorators.py, focusing on no_active_script_draft.

This module tests that the no_active_script_draft decorator correctly blocks
script modification endpoints when:
  - A DB draft record exists for the current revision, OR
  - An in-memory collaborative editing room is non-empty for the current revision

Uses PATCH /api/v1/show/script as the decorated endpoint under test.
"""

from unittest.mock import MagicMock

import tornado.escape

from models.script import Script, ScriptRevision
from models.script_draft import ScriptDraft
from models.show import Show, ShowScriptType
from models.user import User
from test.conftest import DigiScriptTestCase


class TestNoActiveScriptDraftDecorator(DigiScriptTestCase):
    """Test suite for the no_active_script_draft decorator.

    Tests the PATCH /api/v1/show/script endpoint, which is decorated with
    @requires_show, @no_active_script_draft, and @no_live_session.
    """

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            user = User(username="admin", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
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
            self.revision_id = revision.id

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def _patch_script(self, body=None):
        """Helper to issue PATCH /api/v1/show/script with auth."""
        if body is None:
            body = {}
        return self.fetch(
            "/api/v1/show/script?page=1",
            method="PATCH",
            body=tornado.escape.json_encode(body),
            headers={"Authorization": f"Bearer {self.token}"},
            raise_error=False,
        )

    def test_no_draft_no_room_passes_through(self):
        """PATCH /show/script is not blocked when there is no draft and no room.

        The decorator should pass through and let the handler run. A non-409
        response code indicates the decorator did not block the request.
        """
        response = self._patch_script()
        self.assertNotEqual(409, response.code)

    def test_db_draft_blocks_with_409(self):
        """PATCH /show/script returns 409 when a DB draft record exists."""
        with self._app.get_db().sessionmaker() as session:
            draft = ScriptDraft(revision_id=self.revision_id)
            session.add(draft)
            session.commit()

        response = self._patch_script()
        self.assertEqual(409, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertIn("collaborative edit in progress", body["message"])

    def test_non_empty_room_blocks_with_409(self):
        """PATCH /show/script returns 409 when an in-memory room has clients.

        This covers the gap where a room exists in memory (clients editing) but
        the 30-second checkpoint hasn't written a ScriptDraft DB record yet.
        """
        mock_room = MagicMock()
        mock_room.is_empty = False
        mock_manager = MagicMock()
        mock_manager.get_active_room.return_value = mock_room
        self._app.room_manager = mock_manager

        try:
            response = self._patch_script()
            self.assertEqual(409, response.code)
            body = tornado.escape.json_decode(response.body)
            self.assertIn("collaborative edit in progress", body["message"])
        finally:
            del self._app.room_manager

    def test_empty_room_passes_through(self):
        """PATCH /show/script is not blocked when the in-memory room is empty.

        An empty room (all clients disconnected, pending eviction) should not
        block the request. The decorator should pass through.
        """
        mock_room = MagicMock()
        mock_room.is_empty = True
        mock_manager = MagicMock()
        mock_manager.get_active_room.return_value = mock_room
        self._app.room_manager = mock_manager

        try:
            response = self._patch_script()
            self.assertNotEqual(409, response.code)
        finally:
            del self._app.room_manager
