"""Tests for web_decorators.py, focusing on no_active_script_draft.

This module tests that the no_active_script_draft decorator correctly blocks
script modification endpoints when:
  - A DB draft record exists for the current revision, OR
  - An in-memory collaborative editing room is non-empty for the current revision

Uses PATCH /api/v1/show/script as the decorated endpoint under test.
"""

from unittest.mock import MagicMock

import tornado.escape

from models.script_draft import ScriptDraft
from models.user import User
from test.conftest import DigiScriptTestCase
from test.helpers.script_fixtures import create_show_script_revision


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

            show, script, revision = create_show_script_revision(
                session, description="Initial"
            )
            self.show_id = show.id
            self.script_id = script.id
            self.revision_id = revision.id
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

    def test_room_with_an_editor_blocks_with_409(self):
        """PATCH /show/script returns 409 when an in-memory room has an editor.

        This covers the gap where a room exists in memory (clients editing) but
        the 30-second checkpoint hasn't written a ScriptDraft DB record yet.
        """
        mock_room = MagicMock()
        mock_room.has_editors = True
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

    def test_room_with_no_editor_passes_through(self):
        """PATCH /show/script is not blocked when the in-memory room has no
        editor — including a room with only a viewer in it (Phase 4 Step A: a
        mere viewer watching the live draft has no active edit to protect
        against colliding with).
        """
        mock_room = MagicMock()
        mock_room.has_editors = False
        # A real room with a viewer in it is not empty — set explicitly so this
        # test actually distinguishes the has_editors fix from the old
        # `not room.is_empty` check, rather than relying on MagicMock's
        # unconfigured (truthy) default for is_empty to happen to pass too.
        mock_room.is_empty = False
        mock_manager = MagicMock()
        mock_manager.get_active_room.return_value = mock_room
        self._app.room_manager = mock_manager

        try:
            response = self._patch_script()
            self.assertNotEqual(409, response.code)
        finally:
            del self._app.room_manager


class TestRequireAdminDecorator(DigiScriptTestCase):
    """require_admin: 401 when not logged in, 403 for a logged-in non-admin."""

    def _grant(self, token=None):
        return self.fetch(
            "/api/v1/rbac/user/roles/grant",
            method="POST",
            body="{}",
            headers={"Authorization": f"Bearer {token}"} if token else {},
            raise_error=False,
        )

    def test_unauthenticated_is_401(self):
        self.assertEqual(401, self._grant().code)

    def test_non_admin_is_403(self):
        admin_token = self._create_and_login_admin()
        user_token = self._create_and_login_user(admin_token)
        self.assertEqual(403, self._grant(user_token).code)
