"""Integration tests for WebSocket controller query patterns.

These tests connect to the WebSocket endpoint and send messages to trigger
the query patterns in ws_controller.py, following our endpoint-based testing approach.
"""

import asyncio
import base64
import json
from datetime import timedelta
from unittest.mock import AsyncMock

import pycrdt
from sqlalchemy import select
from tornado.httpclient import HTTPRequest
from tornado.testing import gen_test
from tornado.websocket import websocket_connect

from models.script import Script
from models.script_draft import ScriptDraft
from models.session import Session, ShowSession
from models.show import Show
from models.user import User
from services.password_service import PasswordService
from test.conftest import DigiScriptTestCase
from test.helpers.script_fixtures import create_show_script_revision
from utils.script_room_manager import ScriptRoom
from utils.web.pending_disconnects import (
    disconnect_key,
    provisional_key,
    room_close_key,
)


class _WSTestHelpers:
    """Shared WS test helpers.

    NOT a DigiScriptTestCase subclass on purpose — mixed into test classes
    alongside DigiScriptTestCase so pytest/unittest never discovers this
    class itself as a test case, and so subclasses share these methods
    without inheriting each other's test_* methods (which plain TestCase
    inheritance would silently re-run under the subclass too).
    """

    async def _connect_and_auth(self, user_id=None):
        """Connect WS and authenticate.

        :param user_id: User ID to authenticate as. If None, no auth is done.
        :returns: Tuple of (ws, internal_uuid).
        """
        ws_url = self.get_url("/api/v1/ws").replace("http://", "ws://")
        ws = await websocket_connect(ws_url)
        msg = await ws.read_message()
        uuid = json.loads(msg)["DATA"]
        await ws.read_message()  # GET_SETTINGS
        if user_id:
            token = self._app.jwt_service.create_access_token(data={"user_id": user_id})
            await ws.write_message(
                json.dumps({"OP": "AUTHENTICATE", "DATA": {"token": token}})
            )
            await ws.read_message()  # WS_AUTH_SUCCESS
        return ws, uuid


class TestWSControllerIntegration(_WSTestHelpers, DigiScriptTestCase):
    """Test WebSocket controller query patterns via WebSocket connections."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            # Admin user for tests that should succeed
            admin = User(username="admin", password="hashed", is_admin=True)
            session.add(admin)
            session.flush()
            self.admin_id = admin.id

            # Regular user without WRITE role (for RBAC rejection tests)
            viewer = User(username="viewer", password="hashed", is_admin=False)
            session.add(viewer)
            session.flush()
            self.viewer_id = viewer.id

            # Legacy test user alias
            self.user_id = self.admin_id

            # Show + Script + Revision (needed for RBAC and draft checks)
            show, _script, revision = create_show_script_revision(session)
            self.show_id = show.id
            self.revision_id = revision.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        # These tests exercise the collaborative editor.
        self._app.digi_settings.settings["collaborative_script_editing"].set_value(True)

    # ------------------------------------------------------------------
    # REQUEST_SCRIPT_EDIT tests
    # ------------------------------------------------------------------

    @gen_test
    async def test_request_script_edit_no_editors(self):
        """Admin requests edit when no editors exist — should succeed."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response_data["ACTION"])

        # Verify session marked as editor
        with self._app.get_db().sessionmaker() as db_session:
            editors = db_session.scalars(select(Session).where(Session.is_editor)).all()
            self.assertEqual(1, len(editors))
            self.assertTrue(editors[0].is_editor)

        ws.close()

    @gen_test
    async def test_request_script_edit_multi_editor_allowed(self):
        """Second editor request is now allowed (multi-editor mode).

        With CRDTs handling conflicts, multiple editors can co-exist.
        """
        # Create an existing editor session
        with self._app.get_db().sessionmaker() as session:
            editor_session = Session(
                internal_id="existing-editor",
                user_id=self.admin_id,
                is_editor=True,
            )
            session.add(editor_session)
            session.commit()

        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )

        # Multi-editor: should succeed with GET_SCRIPT_CONFIG_STATUS
        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response_data["ACTION"])

        # Verify 2 editor sessions now exist
        with self._app.get_db().sessionmaker() as db_session:
            editors = db_session.scalars(select(Session).where(Session.is_editor)).all()
            self.assertEqual(2, len(editors))

        ws.close()

    @gen_test
    async def test_request_script_edit_blocked_by_cutter(self):
        """Edit request is blocked when another session is cutting."""
        with self._app.get_db().sessionmaker() as session:
            cutter_session = Session(
                internal_id="cutter-session",
                user_id=self.admin_id,
                is_cutting=True,
            )
            session.add(cutter_session)
            session.commit()

        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("REQUEST_EDIT_FAILURE", response_data["ACTION"])
        self.assertIn("cuts mode", response_data["DATA"]["reason"])

        ws.close()

    @gen_test
    async def test_request_edit_rbac_rejection(self):
        """Non-admin user without WRITE role is rejected."""
        ws, uuid = await self._connect_and_auth(self.viewer_id)

        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("REQUEST_EDIT_FAILURE", response_data["ACTION"])
        self.assertIn("permissions", response_data["DATA"]["reason"])

        ws.close()

    # ------------------------------------------------------------------
    # REQUEST_SCRIPT_CUTS tests
    # ------------------------------------------------------------------

    @gen_test
    async def test_request_script_cuts_success(self):
        """Cuts request succeeds when no editors and no draft exist."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_CUTS", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response_data["ACTION"])

        # Verify session marked as cutting
        with self._app.get_db().sessionmaker() as db_session:
            cutters = db_session.scalars(
                select(Session).where(Session.is_cutting)
            ).all()
            self.assertEqual(1, len(cutters))
            self.assertTrue(cutters[0].is_cutting)

        ws.close()

    @gen_test
    async def test_request_script_cuts_blocked_by_editor(self):
        """Cuts request is blocked when an editor session exists."""
        with self._app.get_db().sessionmaker() as session:
            editor_session = Session(
                internal_id="editor-session",
                user_id=self.admin_id,
                is_editor=True,
            )
            session.add(editor_session)
            session.commit()

        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_CUTS", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("REQUEST_EDIT_FAILURE", response_data["ACTION"])
        self.assertIn("editing", response_data["DATA"]["reason"])

        ws.close()

    @gen_test
    async def test_request_script_cuts_blocked_by_draft(self):
        """Cuts request is blocked when an unsaved draft exists."""
        with self._app.get_db().sessionmaker() as session:
            draft = ScriptDraft(revision_id=self.revision_id, data_path="/tmp/test.yjs")
            session.add(draft)
            session.commit()

        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_CUTS", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("REQUEST_EDIT_FAILURE", response_data["ACTION"])
        self.assertIn("draft", response_data["DATA"]["reason"])

        ws.close()

    @gen_test
    async def test_request_script_cuts_allowed_with_viewer_room(self):
        """Cuts request succeeds when room has only viewer clients (no editors)."""
        # Simulate a viewer-only room via the room manager
        doc = pycrdt.Doc()
        doc.get("meta", type=pycrdt.Map)
        doc.get("pages", type=pycrdt.Map)
        doc.get("deleted_line_ids", type=pycrdt.Array)
        room = ScriptRoom(self.revision_id, doc)

        mock_viewer_ws = AsyncMock()
        room.add_client(mock_viewer_ws, "viewer")

        # Inject room into room_manager
        self._app.room_manager._room = room

        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_CUTS", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response_data["ACTION"])

        # Verify session marked as cutting
        with self._app.get_db().sessionmaker() as db_session:
            cutters = db_session.scalars(
                select(Session).where(Session.is_cutting)
            ).all()
            self.assertEqual(1, len(cutters))

        # Clean up
        self._app.room_manager._room = None
        ws.close()

    # ------------------------------------------------------------------
    # STOP_SCRIPT_EDIT tests
    # ------------------------------------------------------------------

    @gen_test
    async def test_stop_script_edit_clears_both_flags(self):
        """STOP_SCRIPT_EDIT clears both is_editor and is_cutting flags."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Set both flags directly in DB
        with self._app.get_db().sessionmaker() as db_session:
            entry = db_session.get(Session, uuid)
            entry.is_editor = True
            entry.is_cutting = True
            db_session.commit()

        await ws.write_message(json.dumps({"OP": "STOP_SCRIPT_EDIT", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response_data["ACTION"])

        # Verify both flags cleared
        with self._app.get_db().sessionmaker() as db_session:
            entry = db_session.get(Session, uuid)
            self.assertFalse(entry.is_editor)
            self.assertFalse(entry.is_cutting)

        ws.close()

    # ------------------------------------------------------------------
    # Disconnect tests
    # ------------------------------------------------------------------

    @gen_test
    async def test_disconnect_clears_is_cutting(self):
        """Disconnecting while cutting triggers GET_SCRIPT_CONFIG_STATUS."""
        # Genuine disconnect: finalisation (cut lock release) is deferred by the reconnect
        # grace window, so shrink it to 0 to assert the post-window outcome.
        self._app.pending_disconnects.grace_seconds = 0
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter cuts mode
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_CUTS", "DATA": {}}))
        await ws.read_message()  # Consume GET_SCRIPT_CONFIG_STATUS

        # Connect observer
        ws_observer, _ = await self._connect_and_auth()

        # Close the cutter
        ws.close()

        # Observer should receive GET_SCRIPT_CONFIG_STATUS
        response = await ws_observer.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response_data["ACTION"])

        # Verify session deleted
        with self._app.get_db().sessionmaker() as db_session:
            entry = db_session.get(Session, uuid)
            self.assertIsNone(entry)

        ws_observer.close()

    # ------------------------------------------------------------------
    # Leader election tests (unchanged from original)
    # ------------------------------------------------------------------

    @gen_test
    async def test_websocket_close_elects_leader(self):
        """Test leader election when WebSocket closes during live session."""
        # Genuine disconnect: finalisation (leader election) is deferred by the reconnect
        # grace window, so shrink it to 0 to assert the post-window outcome.
        self._app.pending_disconnects.grace_seconds = 0
        # Connect first WebSocket (will be the leader)
        ws_url = self.get_url("/api/v1/ws").replace("http://", "ws://")
        ws1 = await websocket_connect(ws_url)

        # Get the UUID for first connection
        msg1 = await ws1.read_message()
        ws1_uuid = json.loads(msg1)["DATA"]
        await ws1.read_message()  # Consume GET_SETTINGS

        # Connect second WebSocket (same user, will become new leader)
        ws2 = await websocket_connect(ws_url)
        msg2 = await ws2.read_message()
        ws2_uuid = json.loads(msg2)["DATA"]
        await ws2.read_message()  # Consume GET_SETTINGS

        # Update both sessions to have the same user_id
        with self._app.get_db().sessionmaker() as session:
            sess1 = session.get(Session, ws1_uuid)
            sess2 = session.get(Session, ws2_uuid)
            sess1.user_id = self.user_id
            sess2.user_id = self.user_id
            session.flush()

            # Create the show session controlled by first WebSocket
            show_session = ShowSession(
                show_id=self.show_id,
                script_revision_id=self.revision_id,
                user_id=self.user_id,
                client_internal_id=ws1_uuid,
            )
            session.add(show_session)
            session.flush()

            show = session.get(Show, self.show_id)
            show.current_session_id = show_session.id
            session.commit()

        # Close the first WebSocket (leader) - this triggers leader election
        ws1.close()

        # Wait for and verify ELECTED_LEADER message sent to second WebSocket
        response = await ws2.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("ELECTED_LEADER", response_data["ACTION"])

        # Verify the show session now points to second WebSocket
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            show_session = session.get(ShowSession, show.current_session_id)
            self.assertEqual(ws2_uuid, show_session.client_internal_id)

        ws2.close()

    @gen_test
    async def test_websocket_close_no_next_leader(self):
        """Test leader election when no other session exists for user."""
        # Genuine disconnect: finalisation (NO_LEADER) is deferred by the reconnect
        # grace window, so shrink it to 0 to assert the post-window outcome.
        self._app.pending_disconnects.grace_seconds = 0
        # Connect WebSocket (will be the only session for this user)
        ws_url = self.get_url("/api/v1/ws").replace("http://", "ws://")
        ws1 = await websocket_connect(ws_url)

        # Get the UUID
        msg1 = await ws1.read_message()
        ws1_uuid = json.loads(msg1)["DATA"]
        await ws1.read_message()  # Consume GET_SETTINGS

        # Connect observer WebSocket (different user, to receive NO_LEADER)
        ws_observer = await websocket_connect(ws_url)
        await ws_observer.read_message()  # Consume SET_UUID
        await ws_observer.read_message()  # Consume GET_SETTINGS

        # Set up the live session
        with self._app.get_db().sessionmaker() as session:
            sess1 = session.get(Session, ws1_uuid)
            sess1.user_id = self.user_id
            session.flush()

            # Create show session
            show_session = ShowSession(
                show_id=self.show_id,
                script_revision_id=self.revision_id,
                user_id=self.user_id,
                client_internal_id=ws1_uuid,
            )
            session.add(show_session)
            session.flush()

            show = session.get(Show, self.show_id)
            show.current_session_id = show_session.id
            session.commit()

        # Close the WebSocket - should trigger NO_LEADER
        ws1.close()

        # Verify observer receives NO_LEADER message
        response = await ws_observer.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("NO_LEADER", response_data["ACTION"])

        ws_observer.close()

    # ------------------------------------------------------------------
    # REQUEST_SCRIPT_CUTS — blocked by other cutter
    # ------------------------------------------------------------------

    @gen_test
    async def test_request_script_cuts_blocked_by_other_cutter(self):
        """Cuts request is blocked when another session is already cutting."""
        with self._app.get_db().sessionmaker() as session:
            cutter_session = Session(
                internal_id="existing-cutter",
                user_id=self.admin_id,
                is_cutting=True,
            )
            session.add(cutter_session)
            session.commit()

        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_CUTS", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("REQUEST_EDIT_FAILURE", response_data["ACTION"])
        self.assertIn("already cutting", response_data["DATA"]["reason"])

        ws.close()

    # ------------------------------------------------------------------
    # JOIN_SCRIPT_ROOM — server-side revision lookup, role from session
    # ------------------------------------------------------------------

    @gen_test
    async def test_join_script_room_no_show_rejected(self):
        """JOIN_SCRIPT_ROOM is rejected with COLLAB_ERROR when no show is loaded."""
        # Clear current show
        self._app.digi_settings.settings["current_show"].set_to_default()

        ws, uuid = await self._connect_and_auth(self.admin_id)
        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("COLLAB_ERROR", response_data["ACTION"])
        self.assertIn("No show loaded", response_data["DATA"]["error"])

        ws.close()

    @gen_test
    async def test_join_script_room_no_active_revision_rejected(self):
        """JOIN_SCRIPT_ROOM is rejected with COLLAB_ERROR when no revision is active."""
        # Remove current_revision from the script
        with self._app.get_db().sessionmaker() as session:
            script = session.scalar(
                select(Script).where(Script.show_id == self.show_id)
            )
            script.current_revision = None
            session.commit()

        ws, uuid = await self._connect_and_auth(self.admin_id)
        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("COLLAB_ERROR", response_data["ACTION"])
        self.assertIn("No active revision", response_data["DATA"]["error"])

        ws.close()

    @gen_test
    async def test_join_script_room_viewer_when_not_editing(self):
        """Admin who hasn't entered edit mode joins room as viewer."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Join room WITHOUT requesting edit first
        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))

        # First message: YJS_SYNC (initial state)
        sync_msg = await ws.read_message()
        sync_data = json.loads(sync_msg)
        self.assertEqual("NOOP", sync_data["OP"])
        self.assertEqual("YJS_SYNC", sync_data["ACTION"])

        # Second message: ROOM_MEMBERS broadcast
        members_msg = await ws.read_message()
        members_data = json.loads(members_msg)
        self.assertEqual("NOOP", members_data["OP"])
        self.assertEqual("ROOM_MEMBERS", members_data["ACTION"])
        members = members_data["DATA"]["members"]
        self.assertEqual(1, len(members))
        self.assertEqual("viewer", members[0]["role"])
        self.assertTrue(members[0]["client_id"])

        ws.close()

    @gen_test
    async def test_request_edit_upgrades_room_role(self):
        """Admin joins room as viewer, then requests edit — role upgrades to editor."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Join room first (as viewer, since not yet editing)
        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        members_msg = await ws.read_message()
        members_data = json.loads(members_msg)
        self.assertEqual("viewer", members_data["DATA"]["members"][0]["role"])
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Now request edit — should upgrade role
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )

        # Should receive ROOM_MEMBERS with upgraded role
        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("ROOM_MEMBERS", response_data["ACTION"])
        self.assertEqual("editor", response_data["DATA"]["members"][0]["role"])

        # Also receive GET_SCRIPT_CONFIG_STATUS
        config_msg = await ws.read_message()
        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", json.loads(config_msg)["ACTION"])

        ws.close()

    @gen_test
    async def test_stop_edit_downgrades_room_role(self):
        """Editor sends STOP_SCRIPT_EDIT — role downgrades to viewer."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        # Join room (as editor)
        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        members_msg = await ws.read_message()
        self.assertEqual(
            "editor", json.loads(members_msg)["DATA"]["members"][0]["role"]
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Stop editing — should downgrade to viewer, then close room (last editor)
        await ws.write_message(json.dumps({"OP": "STOP_SCRIPT_EDIT", "DATA": {}}))

        # Should receive ROOM_MEMBERS with viewer role
        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("ROOM_MEMBERS", response_data["ACTION"])
        self.assertEqual("viewer", response_data["DATA"]["members"][0]["role"])

        # Room closes since this was the last editor
        room_closed_msg = await ws.read_message()
        room_closed_data = json.loads(room_closed_msg)
        self.assertEqual("NOOP", room_closed_data["OP"])
        self.assertEqual("ROOM_CLOSED", room_closed_data["ACTION"])

        # Also receive GET_SCRIPT_CONFIG_STATUS
        config_msg = await ws.read_message()
        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", json.loads(config_msg)["ACTION"])

        ws.close()

    @gen_test
    async def test_stop_edit_triggers_checkpoint_when_last_editor(self):
        """Last editor stops editing — checkpoint is created."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        # Join room (as editor)
        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Make a modification to mark the doc dirty
        room = self._app.room_manager.get_active_room()
        meta = room.doc.get("meta", type=pycrdt.Map)
        meta["test_dirty"] = "value"

        # Stop editing (last editor) — should trigger checkpoint + room close
        await ws.write_message(json.dumps({"OP": "STOP_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_REVISIONS (broadcast after checkpoint)
        # Room is closed after checkpoint — client receives ROOM_CLOSED
        room_closed_msg = await ws.read_message()
        room_closed_data = json.loads(room_closed_msg)
        self.assertEqual("NOOP", room_closed_data["OP"])
        self.assertEqual("ROOM_CLOSED", room_closed_data["ACTION"])
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        # Verify a ScriptDraft record was created (checkpoint happened)
        with self._app.get_db().sessionmaker() as db_session:
            draft = db_session.scalar(
                select(ScriptDraft).where(ScriptDraft.revision_id == self.revision_id)
            )
            self.assertIsNotNone(draft)
            self.assertIsNotNone(draft.data_path)

        # Verify room was evicted
        self.assertIsNone(self._app.room_manager.get_active_room())

        ws.close()

    @gen_test
    async def test_join_script_room_editor_when_editing(self):
        """Admin who entered edit mode joins room as editor."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode first
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # Consume GET_SCRIPT_CONFIG_STATUS

        # Now join room
        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))

        # First message: YJS_SYNC (initial state)
        sync_msg = await ws.read_message()
        sync_data = json.loads(sync_msg)
        self.assertEqual("NOOP", sync_data["OP"])
        self.assertEqual("YJS_SYNC", sync_data["ACTION"])

        # Second message: ROOM_MEMBERS broadcast
        members_msg = await ws.read_message()
        members_data = json.loads(members_msg)
        self.assertEqual("NOOP", members_data["OP"])
        self.assertEqual("ROOM_MEMBERS", members_data["ACTION"])
        members = members_data["DATA"]["members"]
        self.assertEqual(1, len(members))
        self.assertEqual("editor", members[0]["role"])

        ws.close()

    @gen_test
    async def test_stop_edit_closes_room_when_last_editor(self):
        """Last editor sends STOP_SCRIPT_EDIT — room is closed, client gets ROOM_CLOSED."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Verify room exists
        self.assertIsNotNone(self._app.room_manager.get_active_room())

        # Stop editing (last editor)
        await ws.write_message(json.dumps({"OP": "STOP_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # ROOM_MEMBERS

        # Should receive ROOM_CLOSED with empty DATA
        room_closed_msg = await ws.read_message()
        room_closed_data = json.loads(room_closed_msg)
        self.assertEqual("NOOP", room_closed_data["OP"])
        self.assertEqual("ROOM_CLOSED", room_closed_data["ACTION"])
        self.assertEqual({}, room_closed_data["DATA"])

        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        # Room should be evicted
        self.assertIsNone(self._app.room_manager.get_active_room())

        ws.close()

    @gen_test
    async def test_stop_edit_keeps_room_when_other_editors(self):
        """Two editors in room, one stops — room stays open, no ROOM_CLOSED."""
        ws1, uuid1 = await self._connect_and_auth(self.admin_id)
        ws2, uuid2 = await self._connect_and_auth(self.admin_id)

        # Both enter edit mode
        await ws1.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws1.read_message()  # GET_SCRIPT_CONFIG_STATUS for ws1
        await ws2.read_message()  # GET_SCRIPT_CONFIG_STATUS for ws2 (broadcast)

        await ws2.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws1.read_message()  # GET_SCRIPT_CONFIG_STATUS for ws1 (broadcast)
        await ws2.read_message()  # GET_SCRIPT_CONFIG_STATUS for ws2

        # Both join room
        await ws1.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws1.read_message()  # YJS_SYNC
        await ws1.read_message()  # ROOM_MEMBERS
        await ws1.read_message()  # GET_SCRIPT_CONFIG_STATUS from join
        await ws2.read_message()  # GET_SCRIPT_CONFIG_STATUS from join (broadcast)

        await ws2.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws2.read_message()  # YJS_SYNC
        # Both get ROOM_MEMBERS (ws2 joined)
        await ws1.read_message()  # ROOM_MEMBERS for ws1
        await ws2.read_message()  # ROOM_MEMBERS for ws2
        await ws1.read_message()  # GET_SCRIPT_CONFIG_STATUS from join
        await ws2.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # ws1 stops editing — room should stay open (ws2 is still editor)
        await ws1.write_message(json.dumps({"OP": "STOP_SCRIPT_EDIT", "DATA": {}}))

        # Both receive ROOM_MEMBERS (ws1 downgraded to viewer)
        members_msg1 = await ws1.read_message()
        members_msg2 = await ws2.read_message()
        msg1 = json.loads(members_msg1)
        msg2 = json.loads(members_msg2)
        self.assertEqual("NOOP", msg1["OP"])
        self.assertEqual("ROOM_MEMBERS", msg1["ACTION"])
        self.assertEqual("NOOP", msg2["OP"])
        self.assertEqual("ROOM_MEMBERS", msg2["ACTION"])

        # Both receive GET_SCRIPT_CONFIG_STATUS
        await ws1.read_message()
        await ws2.read_message()

        # Room should still exist with the second editor
        room = self._app.room_manager.get_active_room()
        self.assertIsNotNone(room)
        self.assertTrue(room.has_editors)

        ws1.close()
        ws2.close()

    @gen_test
    async def test_disconnect_closes_room_when_last_editor(self):
        """Editor disconnects — remaining viewer receives ROOM_CLOSED."""
        # Genuine disconnect: finalisation (room teardown) is deferred by the reconnect
        # grace window, so shrink it to 0 to assert the post-window outcome.
        self._app.pending_disconnects.grace_seconds = 0
        ws_editor, _ = await self._connect_and_auth(self.admin_id)
        ws_viewer, _ = await self._connect_and_auth(self.admin_id)

        # Editor enters edit mode
        await ws_editor.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws_editor.read_message()  # GET_SCRIPT_CONFIG_STATUS
        await ws_viewer.read_message()  # GET_SCRIPT_CONFIG_STATUS broadcast

        # Both join room
        await ws_editor.write_message(
            json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}})
        )
        await ws_editor.read_message()  # YJS_SYNC
        await ws_editor.read_message()  # ROOM_MEMBERS
        await ws_editor.read_message()  # GET_SCRIPT_CONFIG_STATUS from join
        await ws_viewer.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        await ws_viewer.write_message(
            json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}})
        )
        await ws_viewer.read_message()  # YJS_SYNC
        await ws_editor.read_message()  # ROOM_MEMBERS
        await ws_viewer.read_message()  # ROOM_MEMBERS
        await ws_editor.read_message()  # GET_SCRIPT_CONFIG_STATUS from join
        await ws_viewer.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Editor disconnects
        ws_editor.close()

        # Viewer receives messages in non-deterministic order due to
        # on_close being sync (sends GET_SCRIPT_CONFIG_STATUS immediately)
        # while room broadcast/close happen via add_callback.
        # Collect all messages and verify the expected set by ACTION.
        received_actions = set()
        for _ in range(3):
            msg = json.loads(await ws_viewer.read_message())
            self.assertEqual("NOOP", msg["OP"])
            received_actions.add(msg.get("ACTION"))

        self.assertIn("ROOM_MEMBERS", received_actions)
        self.assertIn("ROOM_CLOSED", received_actions)
        self.assertIn("GET_SCRIPT_CONFIG_STATUS", received_actions)

        # Room should be evicted
        self.assertIsNone(self._app.room_manager.get_active_room())

        ws_viewer.close()

    # ------------------------------------------------------------------
    # SAVE_SCRIPT_DRAFT tests
    # ------------------------------------------------------------------

    @gen_test
    async def test_save_script_draft_success(self):
        """SAVE_SCRIPT_DRAFT dispatches to save_room; editor receives SCRIPT_SAVED."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Send save request. The doc always ends in an empty trailing page, so there is
        # at least one page to report progress for. save_draft always updates
        # meta.last_saved_at in the Y.Doc, so save_room then broadcasts a YJS_UPDATE,
        # and only after that SCRIPT_SAVED (clients rely on that ordering).
        await ws.write_message(json.dumps({"OP": "SAVE_SCRIPT_DRAFT", "DATA": {}}))

        actions = []
        saved = None
        while saved is None:
            response_data = json.loads(await ws.read_message())
            self.assertEqual("NOOP", response_data["OP"])
            actions.append(response_data["ACTION"])
            if response_data["ACTION"] == "SCRIPT_SAVED":
                saved = response_data

        self.assertIn("last_saved_at", saved["DATA"])
        self.assertIn("YJS_UPDATE", actions)
        self.assertLess(actions.index("YJS_UPDATE"), actions.index("SCRIPT_SAVED"))
        self.assertTrue(set(actions) <= {"SAVE_PROGRESS", "YJS_UPDATE", "SCRIPT_SAVED"})

        ws.close()

    @gen_test
    async def test_save_script_draft_error_sent_to_requester(self):
        """If save_draft raises, the requesting editor receives SAVE_ERROR."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Patch the room's save_draft to raise
        room = self._app.room_manager.get_active_room()

        async def _raise_save_error(session):
            raise ValueError("Simulated save failure")

        room.save_draft = _raise_save_error

        await ws.write_message(json.dumps({"OP": "SAVE_SCRIPT_DRAFT", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("SAVE_ERROR", response_data["ACTION"])
        self.assertIn("Simulated save failure", response_data["DATA"]["error"])

        ws.close()

    # ------------------------------------------------------------------
    # DISCARD_SCRIPT_DRAFT tests
    # ------------------------------------------------------------------

    @gen_test
    async def test_discard_script_draft_closes_room(self):
        """DISCARD_SCRIPT_DRAFT closes the room; editor receives ROOM_CLOSED."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        self.assertIsNotNone(self._app.room_manager.get_active_room())

        await ws.write_message(json.dumps({"OP": "DISCARD_SCRIPT_DRAFT", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("ROOM_CLOSED", response_data["ACTION"])
        self.assertEqual({}, response_data["DATA"])

        # Room should be evicted after discard
        self.assertIsNone(self._app.room_manager.get_active_room())

        ws.close()

    # ------------------------------------------------------------------
    # Checkpoint-on-close guard tests
    # ------------------------------------------------------------------

    @gen_test
    async def test_stop_edit_clean_room_does_not_checkpoint(self):
        """Last editor stops editing with a clean room — no checkpoint is written.

        After a save, _dirty is False. STOP_SCRIPT_EDIT should close the room
        without re-creating the draft file or ScriptDraft DB record.
        """
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Confirm the room starts clean (no Y.Doc mutations yet)
        room = self._app.room_manager.get_active_room()
        self.assertFalse(room._dirty)

        # Stop editing (last editor) with a clean room
        await ws.write_message(json.dumps({"OP": "STOP_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # ROOM_CLOSED
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        # No ScriptDraft record should exist
        with self._app.get_db().sessionmaker() as db_session:
            draft = db_session.scalar(
                select(ScriptDraft).where(ScriptDraft.revision_id == self.revision_id)
            )
            self.assertIsNone(draft)

        # Room should still be evicted
        self.assertIsNone(self._app.room_manager.get_active_room())

        ws.close()

    @gen_test
    async def test_stop_edit_dirty_room_checkpoints_before_close(self):
        """Last editor stops editing with a dirty room — checkpoint IS written.

        Any Y.Doc mutation sets _dirty = True. STOP_SCRIPT_EDIT should
        checkpoint (creating a ScriptDraft) before closing the room.
        """
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Mutate the Y.Doc to mark it dirty
        room = self._app.room_manager.get_active_room()
        meta = room.doc.get("meta", type=pycrdt.Map)
        meta["dirty_marker"] = "unsaved"
        self.assertTrue(room._dirty)

        # Stop editing (last editor) with a dirty room
        await ws.write_message(json.dumps({"OP": "STOP_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # ROOM_CLOSED
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        # A ScriptDraft record should have been created by the checkpoint
        with self._app.get_db().sessionmaker() as db_session:
            draft = db_session.scalar(
                select(ScriptDraft).where(ScriptDraft.revision_id == self.revision_id)
            )
            self.assertIsNotNone(draft)
            self.assertIsNotNone(draft.data_path)

        # Room should be evicted
        self.assertIsNone(self._app.room_manager.get_active_room())

    # ------------------------------------------------------------------
    # Corrupt payload handling (Group F gap: F4)
    # ------------------------------------------------------------------

    @gen_test
    async def test_yjs_update_corrupt_payload_returns_collab_error(self):
        """A YJS_UPDATE whose apply_update raises returns COLLAB_ERROR, not a crash."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        room = self._app.room_manager.get_active_room()

        async def _raise_apply_update(_data):
            raise ValueError("Simulated corrupt Yjs payload")

        room.apply_update = _raise_apply_update

        await ws.write_message(
            json.dumps(
                {
                    "OP": "YJS_UPDATE",
                    "DATA": {"payload": base64.b64encode(b"garbage").decode("ascii")},
                }
            )
        )

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("COLLAB_ERROR", response_data["ACTION"])
        self.assertIn("error", response_data["DATA"])

        ws.close()

    @gen_test
    async def test_yjs_sync_step2_corrupt_payload_returns_collab_error(self):
        """A YJS_SYNC step=2 whose apply_update raises returns COLLAB_ERROR."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        room = self._app.room_manager.get_active_room()

        async def _raise_apply_update(_data):
            raise ValueError("Simulated corrupt Yjs sync payload")

        room.apply_update = _raise_apply_update

        await ws.write_message(
            json.dumps(
                {
                    "OP": "YJS_SYNC",
                    "DATA": {
                        "step": 2,
                        "payload": base64.b64encode(b"garbage").decode("ascii"),
                    },
                }
            )
        )

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("COLLAB_ERROR", response_data["ACTION"])
        self.assertIn("error", response_data["DATA"])

        ws.close()


class TestLiveSessionGuards(_WSTestHelpers, DigiScriptTestCase):
    """Tests that live show sessions block collaborative editing operations."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            admin = User(username="admin", password="hashed", is_admin=True)
            session.add(admin)
            session.flush()
            self.admin_id = admin.id

            show, _script, revision = create_show_script_revision(session)
            self.show_id = show.id
            self.revision_id = revision.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        # These tests exercise the collaborative editor.
        self._app.digi_settings.settings["collaborative_script_editing"].set_value(True)

    def _set_live_session_active(self):
        """Create a ShowSession and mark show.current_session_id.

        :returns: The ShowSession ID created.
        """
        with self._app.get_db().sessionmaker() as session:
            show_session = ShowSession(
                show_id=self.show_id,
                script_revision_id=self.revision_id,
            )
            session.add(show_session)
            session.flush()
            show = session.get(Show, self.show_id)
            show.current_session_id = show_session.id
            session.commit()
            return show_session.id

    @gen_test
    async def test_request_script_edit_blocked_by_live_session(self):
        """REQUEST_SCRIPT_EDIT is rejected while a live show session is running."""
        self._set_live_session_active()
        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("REQUEST_EDIT_FAILURE", response_data["ACTION"])
        self.assertIn("live session", response_data["DATA"]["reason"])

        ws.close()

    @gen_test
    async def test_request_script_cuts_blocked_by_live_session(self):
        """REQUEST_SCRIPT_CUTS is rejected while a live show session is running."""
        self._set_live_session_active()
        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_CUTS", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("REQUEST_EDIT_FAILURE", response_data["ACTION"])
        self.assertIn("live session", response_data["DATA"]["reason"])

        ws.close()

    @gen_test
    async def test_join_script_room_blocked_by_live_session(self):
        """JOIN_SCRIPT_ROOM is rejected with COLLAB_ERROR while a live session is running."""
        self._set_live_session_active()
        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("COLLAB_ERROR", response_data["ACTION"])
        self.assertIn("live session", response_data["DATA"]["error"])

        ws.close()

    @gen_test
    async def test_save_script_draft_blocked_by_live_session(self):
        """SAVE_SCRIPT_DRAFT is rejected with COLLAB_ERROR while a live session is running."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room before activating the live session
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Activate live session now that we're in the room
        self._set_live_session_active()

        await ws.write_message(json.dumps({"OP": "SAVE_SCRIPT_DRAFT", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("COLLAB_ERROR", response_data["ACTION"])
        self.assertIn("live session", response_data["DATA"]["error"])

        ws.close()

    @gen_test
    async def test_yjs_update_blocked_by_live_session(self):
        """YJS_UPDATE is rejected with COLLAB_ERROR while a live session is running."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room before activating the live session
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Activate live session now that we're in the room
        self._set_live_session_active()

        await ws.write_message(
            json.dumps(
                {
                    "OP": "YJS_UPDATE",
                    "DATA": {"payload": base64.b64encode(b"").decode("ascii")},
                }
            )
        )

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("COLLAB_ERROR", response_data["ACTION"])
        self.assertIn("live session", response_data["DATA"]["error"])

        ws.close()

    @gen_test
    async def test_yjs_sync_step2_blocked_by_live_session(self):
        """YJS_SYNC step=2 is rejected with COLLAB_ERROR while a live session is running."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room before activating the live session
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Activate live session now that we're in the room
        self._set_live_session_active()

        await ws.write_message(
            json.dumps(
                {
                    "OP": "YJS_SYNC",
                    "DATA": {
                        "step": 2,
                        "payload": base64.b64encode(b"").decode("ascii"),
                    },
                }
            )
        )

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("COLLAB_ERROR", response_data["ACTION"])
        self.assertIn("live session", response_data["DATA"]["error"])

        ws.close()


class TestWSReconnectReclaim(_WSTestHelpers, DigiScriptTestCase):
    """Reload / reconnect semantics for the WS session lifecycle (issue #1419, #1424).

    A browser reload closes the old socket and opens a new one that sends
    ``REFRESH_CLIENT`` with the old uuid. The two sides race: the old handler's
    ``on_close`` can run before *or* after the new handler's ``REFRESH_CLIENT``.
    Each test drives one ordering explicitly, using server-side sync points
    (waiting for the exact handler object to leave ``application.clients``)
    rather than relying on a message that ``on_close`` may or may not send.

    Reconnects mimic client-v3's wire order: ``REFRESH_CLIENT`` then
    ``AUTHENTICATE`` then (after ``WS_AUTH_SUCCESS``) ``NEW_CLIENT``.

    Grace-window timers are stepped deterministically: the window is long
    (``LONG_GRACE``, never waited on) and a test that needs it to expire fires the
    timer through ``PendingDisconnects.fire``. Only the ``*_real_timer`` tests wait
    on wall-clock expiry, with ``SHORT_GRACE``.
    """

    LONG_GRACE = 30.0
    # Real-timer tests must finish a whole reconnect inside this window, so keep
    # it well clear of a slow CI runner's round-trip times.
    SHORT_GRACE = 3.0
    # Wall-clock waits for a SHORT_GRACE timer: the window plus generous headroom.
    TIMER_WAIT = SHORT_GRACE + 5.0

    def setUp(self):
        super().setUp()
        viewer_hash = self.io_loop.run_sync(
            lambda: PasswordService.hash_password("viewerpass")
        )
        with self._app.get_db().sessionmaker() as session:
            admin = User(username="admin", password="hashed", is_admin=True)
            session.add(admin)
            session.flush()
            self.admin_id = admin.id

            viewer = User(username="viewer", password=viewer_hash, is_admin=False)
            session.add(viewer)
            session.flush()
            self.viewer_id = viewer.id

            show, _script, revision = create_show_script_revision(session)
            self.show_id = show.id
            self.revision_id = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self._app.digi_settings.settings["collaborative_script_editing"].set_value(True)
        self._set_grace(self.LONG_GRACE)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_grace(self, seconds):
        """Set the reconnect grace window for this test's app instance.

        :param seconds: Grace window in seconds.
        """
        self._app.pending_disconnects.grace_seconds = seconds

    async def _fire(self, key):
        """Expire the grace-window timer under *key* now, asserting it was scheduled.

        :param key: Timer key (``disconnect_key`` / ``provisional_key`` /
            ``room_close_key``).
        """
        self.assertTrue(
            await self._app.pending_disconnects.fire(key),
            f"no grace-window timer was scheduled under {key}",
        )

    async def _read_until(self, ws, op=None, action=None, timeout=3.0):
        """Read messages until one matches *op* and/or *action*.

        :param ws: Client websocket connection.
        :param op: Required ``OP`` value, or None for any.
        :param action: Required ``ACTION`` value, or None for any.
        :param timeout: Overall time limit in seconds.
        :returns: Tuple of (matching message, list of messages skipped over).
        """
        skipped = []
        deadline = asyncio.get_running_loop().time() + timeout
        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                self.fail(f"Timed out waiting for OP={op} ACTION={action}: {skipped}")
            try:
                raw = await asyncio.wait_for(ws.read_message(), remaining)
            except asyncio.TimeoutError:
                self.fail(f"Timed out waiting for OP={op} ACTION={action}: {skipped}")
            self.assertIsNotNone(raw, "websocket closed while waiting for a message")
            msg = json.loads(raw)
            if (op is None or msg.get("OP") == op) and (
                action is None or msg.get("ACTION") == action
            ):
                return msg, skipped
            skipped.append(msg)

    async def _drain(self, ws, timeout=0.3):
        """Collect every message that arrives on *ws* within *timeout*.

        Used for asserting that something was NOT sent. Only call it last on a
        connection, or accept that it consumes everything pending.

        :param ws: Client websocket connection.
        :param timeout: Quiet period in seconds that ends the drain.
        :returns: List of decoded messages.
        """
        messages = []
        while True:
            try:
                raw = await asyncio.wait_for(ws.read_message(), timeout)
            except asyncio.TimeoutError:
                return messages
            if raw is None:
                return messages
            messages.append(json.loads(raw))

    async def _actions(self, ws, timeout=0.3):
        """Return the ``ACTION`` of every message drained from *ws*."""
        return [m.get("ACTION") for m in await self._drain(ws, timeout)]

    def _token(self, user_id, **kwargs):
        return self._app.jwt_service.create_access_token(
            data={"user_id": user_id}, **kwargs
        )

    async def _authenticate(self, ws, token):
        """Send AUTHENTICATE with *token* and return the auth reply's ``OP``."""
        await ws.write_message(
            json.dumps({"OP": "AUTHENTICATE", "DATA": {"token": token}})
        )
        msg, _ = await self._read_until(ws, op=None, action=None)
        while msg["OP"] not in ("WS_AUTH_SUCCESS", "WS_AUTH_ERROR"):
            msg, _ = await self._read_until(ws)
        return msg["OP"]

    async def _barrier(self, ws, user_id):
        """Round-trip a message so every earlier message on *ws* is processed.

        Tornado runs a connection's ``on_message`` coroutines one at a time, so
        once the ``WS_AUTH_SUCCESS`` reply to a fresh ``AUTHENTICATE`` arrives,
        all previously sent messages on that connection have been handled.

        :param ws: Client websocket connection.
        :param user_id: User to (re-)authenticate as.
        """
        await ws.write_message(
            json.dumps({"OP": "AUTHENTICATE", "DATA": {"token": self._token(user_id)}})
        )
        await self._read_until(ws, op="WS_AUTH_SUCCESS")

    async def _refresh_only(self, old_uuid):
        """Open a connection and send REFRESH_CLIENT for *old_uuid*, without auth.

        :returns: Tuple of (websocket, placeholder uuid from SET_UUID).
        """
        ws, placeholder_uuid = await self._connect_and_auth()
        self.assertNotEqual(old_uuid, placeholder_uuid)
        await ws.write_message(json.dumps({"OP": "REFRESH_CLIENT", "DATA": old_uuid}))
        return ws, placeholder_uuid

    async def _reload(self, old_uuid, user_id, new_client=True):
        """Simulate the reloaded page reconnecting and resuming *old_uuid*.

        :param old_uuid: The uuid the page had before reloading.
        :param user_id: The user the page is logged in as.
        :param new_client: Send NEW_CLIENT after auth (client-v3 does; the legacy
            client only does for a brand-new connection).
        :returns: The new client websocket connection.
        """
        ws, _ = await self._refresh_only(old_uuid)
        await ws.write_message(
            json.dumps({"OP": "AUTHENTICATE", "DATA": {"token": self._token(user_id)}})
        )
        await self._read_until(ws, op="WS_AUTH_SUCCESS")
        if new_client:
            await ws.write_message(json.dumps({"OP": "NEW_CLIENT", "DATA": {}}))
        await self._barrier(ws, user_id)
        return ws

    async def _close_and_wait(self, ws, handler, timeout=3.0):
        """Close *ws* client-side and wait until the server ran *handler*'s on_close.

        Waits on the exact handler object rather than on its uuid, because in
        the stale-handler race two handlers carry the same uuid.

        :param ws: Client websocket connection to close.
        :param handler: The server-side handler for *ws*, captured beforehand.
        :param timeout: Time limit in seconds.
        """
        ws.close()
        deadline = asyncio.get_running_loop().time() + timeout
        while handler in self._app.clients:
            if asyncio.get_running_loop().time() > deadline:
                self.fail("server did not process the websocket close in time")
            await asyncio.sleep(0.01)

    def _start_live_session(self, leader_uuid, user_id):
        """Create a live ShowSession led by *leader_uuid*.

        :param leader_uuid: Session internal_id that holds leadership.
        :param user_id: The user who started the show session.
        """
        with self._app.get_db().sessionmaker() as session:
            show_session = ShowSession(
                show_id=self.show_id,
                script_revision_id=self.revision_id,
                user_id=user_id,
                client_internal_id=leader_uuid,
            )
            session.add(show_session)
            session.flush()
            show = session.get(Show, self.show_id)
            show.current_session_id = show_session.id
            session.commit()

    def _live_session_state(self):
        """Return ``(client_internal_id, last_client_internal_id)`` of the live session."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            show_session = session.get(ShowSession, show.current_session_id)
            return (
                show_session.client_internal_id,
                show_session.last_client_internal_id,
            )

    def _session_row(self, uuid):
        """Return ``(is_editor, is_cutting, user_id)`` for *uuid*, or None if absent."""
        with self._app.get_db().sessionmaker() as session:
            row = session.get(Session, uuid)
            if row is None:
                return None
            return bool(row.is_editor), bool(row.is_cutting), row.user_id

    async def _become_editor(self, ws, observer):
        """Put *ws* into edit mode and consume the resulting broadcasts."""
        await ws.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {"collab": True}})
        )
        await self._read_until(ws, action="GET_SCRIPT_CONFIG_STATUS")
        await self._read_until(observer, action="GET_SCRIPT_CONFIG_STATUS")

    async def _editor_and_observer(self):
        """An admin editor connection plus a viewer observer connection."""
        ws, uuid = await self._connect_and_auth(self.admin_id)
        observer, _ = await self._connect_and_auth(self.viewer_id)
        await self._become_editor(ws, observer)
        self.assertEqual((True, False, self.admin_id), self._session_row(uuid))
        return ws, uuid, observer

    async def _join_room(self, ws):
        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        await self._read_until(ws, action="YJS_SYNC")

    async def _post(self, path, body, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return await self.http_client.fetch(
            HTTPRequest(
                self.get_url(path),
                method="POST",
                body=json.dumps(body),
                headers=headers,
            ),
            raise_error=False,
        )

    # ------------------------------------------------------------------
    # Reload where the old socket's on_close runs first: edit/cut flags
    # ------------------------------------------------------------------

    @gen_test
    async def test_refresh_client_after_stale_close_keeps_is_editor(self):
        """on_close runs first, then REFRESH_CLIENT resumes the uuid as an editor.

        Originally ``test_refresh_client_after_stale_close_loses_is_editor``
        (expectedFailure, commit 4069c74). Adapted: it used on_close's immediate
        GET_SCRIPT_CONFIG_STATUS broadcast as the "on_close has run" signal, which
        a grace window deliberately no longer sends; it now waits on the handler.
        """
        ws1, uuid1, observer = await self._editor_and_observer()

        await self._close_and_wait(ws1, self._app.get_ws(uuid1))
        ws2 = await self._reload(uuid1, self.admin_id)

        row = self._session_row(uuid1)
        self.assertIsNotNone(row, "resumed row for uuid1 is missing")
        self.assertTrue(
            row[0],
            "is_editor did not survive a real reload -- on_close's "
            "unconditional delete raced ahead of REFRESH_CLIENT",
        )
        self.assertIsNotNone(self._app.get_ws(uuid1))
        self.assertFalse(
            self._app.pending_disconnects.is_scheduled(provisional_key(uuid1)),
            "authenticating as the owner should have confirmed the adopted flags",
        )

        observer.close()
        ws2.close()

    @gen_test
    async def test_reload_keeps_is_cutting(self):
        """A reload while in cuts mode keeps is_cutting (on_close first)."""
        ws1, uuid1 = await self._connect_and_auth(self.admin_id)
        observer, _ = await self._connect_and_auth(self.viewer_id)
        await ws1.write_message(json.dumps({"OP": "REQUEST_SCRIPT_CUTS", "DATA": {}}))
        await self._read_until(ws1, action="GET_SCRIPT_CONFIG_STATUS")
        await self._read_until(observer, action="GET_SCRIPT_CONFIG_STATUS")

        await self._close_and_wait(ws1, self._app.get_ws(uuid1))
        ws2 = await self._reload(uuid1, self.admin_id)

        row = self._session_row(uuid1)
        self.assertIsNotNone(row, "resumed row for uuid1 is missing")
        self.assertTrue(row[1], "is_cutting did not survive a reload")
        # Nobody was told the cut lock was released, because it never was.
        self.assertNotIn("GET_SCRIPT_CONFIG_STATUS", await self._actions(observer))

        observer.close()
        ws2.close()

    # ------------------------------------------------------------------
    # Reload where REFRESH_CLIENT runs before the stale socket's on_close
    # ------------------------------------------------------------------

    @gen_test
    async def test_refresh_client_before_stale_close_keeps_is_editor(self):
        """REFRESH_CLIENT resumes uuid1 BEFORE the old socket's on_close runs.

        Originally ``test_refresh_client_before_stale_close_loses_is_editor``
        (expectedFailure, commit 4069c74). Adapted: the stale close is detected by
        waiting on the old handler object, since a correct fix sends no
        GET_SCRIPT_CONFIG_STATUS for it, and instead of relying on a zero grace
        window it asserts that the stale close scheduled no finalisation at all.
        """
        ws1, uuid1, observer = await self._editor_and_observer()
        stale_handler = self._app.get_ws(uuid1)

        # ws2 resumes uuid1 while ws1 is still open server-side.
        ws2 = await self._reload(uuid1, self.admin_id)
        self.assertEqual((True, False, self.admin_id), self._session_row(uuid1))

        # Now the stale ws1 finally closes server-side.
        await self._close_and_wait(ws1, stale_handler)
        await self._barrier(ws2, self.admin_id)

        self.assertFalse(
            self._app.pending_disconnects.is_pending(uuid1),
            "the stale close scheduled finalisation of a row a live handler owns",
        )
        row = self._session_row(uuid1)
        self.assertIsNotNone(
            row,
            "stale ws1's on_close deleted the live, just-resumed uuid1 "
            "row instead of leaving it alone",
        )
        self.assertTrue(row[0])
        self.assertNotIn(
            "GET_SCRIPT_CONFIG_STATUS",
            await self._actions(observer),
            "the stale close announced an edit-lock release that did not happen",
        )

        observer.close()
        ws2.close()

    # ------------------------------------------------------------------
    # Live-show leader reloading a single tab
    # ------------------------------------------------------------------

    @gen_test
    async def test_leader_reload_keeps_leadership_close_first(self):
        """Leader's on_close runs first; the reload resumes leadership silently.

        On the pre-fix code the final holder is also correct (on_close records
        last_client_internal_id and REFRESH_CLIENT reclaims it), but only after
        broadcasting NO_LEADER to every follower mid-reload. The grace window
        must hold leadership instead, so followers never see NO_LEADER.
        """
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)

        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))
        # Held during the window.
        self.assertEqual(uuid_l, self._live_session_state()[0])

        ws_l2 = await self._reload(uuid_l, self.admin_id)

        self.assertEqual(uuid_l, self._live_session_state()[0])
        self.assertNotIn("NO_LEADER", await self._actions(follower))

        follower.close()
        ws_l2.close()

    @gen_test
    async def test_leader_reload_keeps_leadership_refresh_first(self):
        """REFRESH_CLIENT resumes the leader uuid before the stale on_close runs."""
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)
        stale_handler = self._app.get_ws(uuid_l)

        ws_l2 = await self._reload(uuid_l, self.admin_id)
        await self._close_and_wait(ws_l, stale_handler)
        await self._barrier(ws_l2, self.admin_id)

        self.assertFalse(self._app.pending_disconnects.is_pending(uuid_l))
        self.assertIsNotNone(self._session_row(uuid_l), "leader row was deleted")
        self.assertEqual(uuid_l, self._live_session_state()[0])
        self.assertNotIn("NO_LEADER", await self._actions(follower))

        follower.close()
        ws_l2.close()

    # ------------------------------------------------------------------
    # Two tabs of the leader's user, both reloading (#1424)
    # ------------------------------------------------------------------

    async def _two_tab_reload(self, leader_closes_first):
        """Run the #1424 two-tab reload scenario and assert the leader survives.

        Both tabs belong to the same user. The follower reconnects first, the
        adversarial order: its NEW_CLIENT / REFRESH_CLIENT gets the first chance
        to take leadership.

        :param leader_closes_first: Which old socket's on_close runs first.
        """
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        ws_f, uuid_f = await self._connect_and_auth(self.admin_id)
        observer, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)
        h_l = self._app.get_ws(uuid_l)
        h_f = self._app.get_ws(uuid_f)

        if leader_closes_first:
            await self._close_and_wait(ws_l, h_l)
            await self._close_and_wait(ws_f, h_f)
        else:
            await self._close_and_wait(ws_f, h_f)
            await self._close_and_wait(ws_l, h_l)

        ws_f2 = await self._reload(uuid_f, self.admin_id)
        ws_l2 = await self._reload(uuid_l, self.admin_id)

        self.assertEqual(
            uuid_l,
            self._live_session_state()[0],
            "the original leader tab did not end up leader after both tabs reloaded",
        )
        self.assertNotIn(
            "ELECTED_LEADER",
            await self._actions(ws_f2),
            "the follower tab was told it was leader",
        )
        self.assertNotIn("NO_LEADER", await self._actions(observer))

        observer.close()
        ws_f2.close()
        ws_l2.close()

    @gen_test
    async def test_two_tab_reload_original_leader_wins_leader_closes_first(self):
        """#1424: leader's socket closes first, then the follower tab's."""
        await self._two_tab_reload(leader_closes_first=True)

    @gen_test
    async def test_two_tab_reload_original_leader_wins_follower_closes_first(self):
        """#1424: follower tab's socket closes first, then the leader's."""
        await self._two_tab_reload(leader_closes_first=False)

    # ------------------------------------------------------------------
    # Genuine disconnects (no reconnect): held through the window, then
    # released / re-elected
    # ------------------------------------------------------------------

    @gen_test(timeout=25)
    async def test_genuine_disconnect_holds_then_releases_edit_lock_real_timer(self):
        """The edit lock is held through the window, then released and announced.

        Runs on a real (wall-clock) timer, to cover the IOLoop scheduling path.
        """
        self._set_grace(self.SHORT_GRACE)
        ws1, uuid1, observer = await self._editor_and_observer()

        await self._close_and_wait(ws1, self._app.get_ws(uuid1))
        self.assertEqual(
            (True, False, self.admin_id),
            self._session_row(uuid1),
            "the edit lock was released before the reconnect grace window expired",
        )

        await self._read_until(
            observer, action="GET_SCRIPT_CONFIG_STATUS", timeout=self.TIMER_WAIT
        )
        self.assertIsNone(self._session_row(uuid1))
        self.assertFalse(self._app.pending_disconnects.is_pending(uuid1))

        observer.close()

    @gen_test
    async def test_genuine_disconnect_holds_then_elects_leader(self):
        """Leadership is held through the window, then passes to a live same-user tab."""
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        ws_f, uuid_f = await self._connect_and_auth(self.admin_id)
        self._start_live_session(uuid_l, self.admin_id)

        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))
        self.assertEqual(
            uuid_l,
            self._live_session_state()[0],
            "leadership moved before the reconnect grace window expired",
        )

        await self._fire(disconnect_key(uuid_l))
        await self._read_until(ws_f, action="ELECTED_LEADER")
        self.assertEqual((uuid_f, None), self._live_session_state())
        self.assertIsNone(self._session_row(uuid_l))

        ws_f.close()

    @gen_test
    async def test_genuine_disconnect_holds_then_no_leader(self):
        """With no other same-user tab, NO_LEADER is sent once the window expires."""
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)

        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))
        self.assertEqual(
            uuid_l,
            self._live_session_state()[0],
            "leadership was dropped before the reconnect grace window expired",
        )

        await self._fire(disconnect_key(uuid_l))
        await self._read_until(follower, action="NO_LEADER")
        self.assertEqual((None, uuid_l), self._live_session_state())

        follower.close()

    @gen_test
    async def test_election_skips_disconnected_same_user_tab(self):
        """Election never promotes a same-user tab that has itself disconnected.

        The leader's window expires while the other tab is closed and still
        inside its own window (possibly mid-reload). That tab is not a candidate:
        on_close removed it from ``application.clients`` before its uuid became
        pending. (The ``is_pending`` check inside election is only a defensive
        backstop for that invariant and is not what this test exercises.)
        """
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        ws_f, uuid_f = await self._connect_and_auth(self.admin_id)
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)

        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))
        await self._close_and_wait(ws_f, self._app.get_ws(uuid_f))
        self.assertTrue(self._app.pending_disconnects.is_pending(uuid_f))

        await self._fire(disconnect_key(uuid_l))
        await self._read_until(follower, action="NO_LEADER")
        self.assertEqual((None, uuid_l), self._live_session_state())

        follower.close()

    @gen_test
    async def test_election_prefers_earliest_connected_candidate(self):
        """With two eligible live same-user tabs, the earlier connection wins."""
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        ws_a, uuid_a = await self._connect_and_auth(self.admin_id)
        ws_b, uuid_b = await self._connect_and_auth(self.admin_id)
        self._start_live_session(uuid_l, self.admin_id)

        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))
        await self._fire(disconnect_key(uuid_l))

        await self._read_until(ws_a, action="ELECTED_LEADER")
        self.assertEqual((uuid_a, None), self._live_session_state())
        self.assertNotIn("ELECTED_LEADER", await self._actions(ws_b))

        ws_a.close()
        ws_b.close()

    @gen_test
    async def test_finalise_retries_when_commit_fails(self):
        """A failed row delete neither announces a release nor elects; it retries."""
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        await self._become_editor(
            ws_l, (await self._connect_and_auth(self.viewer_id))[0]
        )
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)
        handler = self._app.get_ws(uuid_l)
        await self._close_and_wait(ws_l, handler)

        real_make_session = handler.make_session
        handler.make_session = lambda: (_ for _ in ()).throw(
            RuntimeError("database is locked")
        )
        await self._fire(disconnect_key(uuid_l))
        handler.make_session = real_make_session

        self.assertEqual((True, False, self.admin_id), self._session_row(uuid_l))
        self.assertEqual(uuid_l, self._live_session_state()[0])
        self.assertTrue(
            self._app.pending_disconnects.is_pending(uuid_l), "no retry was scheduled"
        )

        await self._fire(disconnect_key(uuid_l))
        await self._read_until(follower, action="NO_LEADER")
        self.assertIsNone(self._session_row(uuid_l))

        follower.close()

    # ------------------------------------------------------------------
    # Leadership coming back after the window has expired
    # ------------------------------------------------------------------

    async def _expired_leader(self):
        """Leader disconnects for good; returns (uuid, follower connection)."""
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)
        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))
        await self._fire(disconnect_key(uuid_l))
        await self._read_until(follower, action="NO_LEADER")
        self.assertEqual((None, uuid_l), self._live_session_state())
        return uuid_l, follower

    @gen_test
    async def test_late_reload_by_leader_reclaims_leadership(self):
        """The departed leader reclaims leadership once it authenticates again."""
        uuid_l, follower = await self._expired_leader()

        ws_l2, _ = await self._refresh_only(uuid_l)
        # Not before auth: REFRESH_CLIENT alone proves nothing.
        await asyncio.sleep(0.05)
        self.assertEqual((None, uuid_l), self._live_session_state())

        await ws_l2.write_message(
            json.dumps(
                {"OP": "AUTHENTICATE", "DATA": {"token": self._token(self.admin_id)}}
            )
        )
        await self._read_until(ws_l2, action="ELECTED_LEADER")
        self.assertEqual((uuid_l, None), self._live_session_state())

        follower.close()
        ws_l2.close()

    @gen_test
    async def test_late_reload_legacy_order_reclaims_leadership(self):
        """The legacy client never sends NEW_CLIENT on a refresh; reclaim still works."""
        uuid_l, follower = await self._expired_leader()
        ws_l2 = await self._reload(uuid_l, self.admin_id, new_client=False)
        self.assertEqual((uuid_l, None), self._live_session_state())
        follower.close()
        ws_l2.close()

    @gen_test
    async def test_late_reload_of_leader_uuid_by_other_user_does_not_reclaim(self):
        """Presenting the departed leader's uuid as a different user claims nothing."""
        uuid_l, follower = await self._expired_leader()
        ws_x = await self._reload(uuid_l, self.viewer_id)
        self.assertEqual((None, uuid_l), self._live_session_state())
        self.assertNotIn("ELECTED_LEADER", await self._actions(ws_x))
        follower.close()
        ws_x.close()

    @gen_test
    async def test_late_unauthenticated_reload_of_leader_uuid_does_not_reclaim(self):
        """An unauthenticated REFRESH_CLIENT of the departed leader's uuid claims nothing."""
        uuid_l, follower = await self._expired_leader()
        ws_x, _ = await self._refresh_only(uuid_l)
        self.assertNotIn("ELECTED_LEADER", await self._actions(ws_x))
        self.assertEqual((None, uuid_l), self._live_session_state())
        follower.close()
        ws_x.close()

    @gen_test
    async def test_late_reload_of_non_leader_uuid_does_not_reclaim(self):
        """A same-user tab that was never the leader does not take leadership back
        through the reclaim path (legacy wire order, so NEW_CLIENT plays no part).
        """
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        ws_f, uuid_f = await self._connect_and_auth(self.admin_id)
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)
        await self._close_and_wait(ws_f, self._app.get_ws(uuid_f))
        await self._fire(disconnect_key(uuid_f))
        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))
        await self._fire(disconnect_key(uuid_l))
        await self._read_until(follower, action="NO_LEADER")

        ws_f2 = await self._reload(uuid_f, self.admin_id, new_client=False)
        self.assertEqual((None, uuid_l), self._live_session_state())

        follower.close()
        ws_f2.close()

    @gen_test
    async def test_late_reload_reclaims_only_if_no_one_else_leads(self):
        """After the window expires, a returning leader cannot steal leadership
        from a tab that NEW_CLIENT legitimately promoted in the meantime.
        """
        uuid_l, follower = await self._expired_leader()

        # A brand-new tab of the same user connects and claims leadership.
        ws_new, uuid_new = await self._connect_and_auth(self.admin_id)
        await ws_new.write_message(json.dumps({"OP": "NEW_CLIENT", "DATA": {}}))
        await self._read_until(ws_new, action="ELECTED_LEADER")
        self.assertEqual((uuid_new, None), self._live_session_state())

        # The old leader's page finally comes back.
        ws_l2 = await self._reload(uuid_l, self.admin_id)
        self.assertEqual(uuid_new, self._live_session_state()[0])

        follower.close()
        ws_new.close()
        ws_l2.close()

    # ------------------------------------------------------------------
    # State adopted by REFRESH_CLIENT is provisional until auth confirms it
    # ------------------------------------------------------------------

    @gen_test
    async def test_adopted_flags_released_when_auth_fails(self):
        """An adopted edit lock is dropped at once if AUTHENTICATE fails
        (e.g. the editor reloads with an expired token).
        """
        ws1, uuid1, observer = await self._editor_and_observer()
        await self._close_and_wait(ws1, self._app.get_ws(uuid1))

        ws2, _ = await self._refresh_only(uuid1)
        expired = self._token(self.admin_id, expires_delta=timedelta(seconds=-10))
        self.assertEqual("WS_AUTH_ERROR", await self._authenticate(ws2, expired))

        await self._read_until(observer, action="GET_SCRIPT_CONFIG_STATUS")
        self.assertEqual((False, False, self.admin_id), self._session_row(uuid1))
        self.assertFalse(
            self._app.pending_disconnects.is_scheduled(provisional_key(uuid1))
        )

        observer.close()
        ws2.close()

    @gen_test
    async def test_adopted_flags_released_on_authenticate_without_token(self):
        """AUTHENTICATE with no token also revokes adopted state straight away."""
        ws1, uuid1, observer = await self._editor_and_observer()
        await self._close_and_wait(ws1, self._app.get_ws(uuid1))

        ws2, _ = await self._refresh_only(uuid1)
        await ws2.write_message(json.dumps({"OP": "AUTHENTICATE", "DATA": {}}))
        await self._read_until(ws2, op="WS_AUTH_ERROR")

        await self._read_until(observer, action="GET_SCRIPT_CONFIG_STATUS")
        self.assertEqual((False, False, self.admin_id), self._session_row(uuid1))

        observer.close()
        ws2.close()

    @gen_test
    async def test_adopted_flags_expire_without_authentication(self):
        """A resumed tab that never authenticates (e.g. logged out) loses the lock
        when its provisional window expires.
        """
        ws1, uuid1, observer = await self._editor_and_observer()
        await self._close_and_wait(ws1, self._app.get_ws(uuid1))

        ws2, _ = await self._refresh_only(uuid1)
        await asyncio.sleep(0.05)
        # Still held inside the window.
        self.assertEqual((True, False, self.admin_id), self._session_row(uuid1))

        await self._fire(provisional_key(uuid1))
        await self._read_until(observer, action="GET_SCRIPT_CONFIG_STATUS")
        self.assertEqual((False, False, self.admin_id), self._session_row(uuid1))

        observer.close()
        ws2.close()

    @gen_test
    async def test_resumed_row_drops_flags_when_user_changes(self):
        """Resuming another user's uuid does not inherit their edit lock, and the
        release is announced.
        """
        ws1, uuid1, observer = await self._editor_and_observer()
        await self._close_and_wait(ws1, self._app.get_ws(uuid1))

        ws2 = await self._reload(uuid1, self.viewer_id)

        self.assertEqual((False, False, self.viewer_id), self._session_row(uuid1))
        await self._read_until(observer, action="GET_SCRIPT_CONFIG_STATUS")

        observer.close()
        ws2.close()

    @gen_test
    async def test_rest_login_as_other_user_on_resumed_uuid_drops_flags(self):
        """The REST login path cannot bind a different user onto an editor's row
        and keep the lock (REFRESH_CLIENT, then POST /auth/login with session_id).
        """
        ws1, uuid1, observer = await self._editor_and_observer()
        ws2, _ = await self._refresh_only(uuid1)
        await asyncio.sleep(0.05)

        response = await self._post(
            "/api/v1/auth/login",
            {"username": "viewer", "password": "viewerpass", "session_id": uuid1},
        )
        self.assertEqual(200, response.code)
        self.assertEqual((False, False, self.viewer_id), self._session_row(uuid1))
        await self._read_until(observer, action="GET_SCRIPT_CONFIG_STATUS")

        # The follow-up WS AUTHENTICATE as that user does not bring it back.
        self.assertEqual(
            "WS_AUTH_SUCCESS",
            await self._authenticate(ws2, self._token(self.viewer_id)),
        )
        self.assertEqual((False, False, self.viewer_id), self._session_row(uuid1))

        observer.close()
        ws1.close()
        ws2.close()

    @gen_test
    async def test_other_user_resuming_leader_uuid_hands_leadership_on(self):
        """A different user who resumes the leader's uuid in the window does not
        lead. Leadership passes to a live tab of the show's user.
        """
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        ws_a, uuid_a = await self._connect_and_auth(self.admin_id)
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)
        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))

        ws_x = await self._reload(uuid_l, self.viewer_id)

        await self._read_until(ws_a, action="ELECTED_LEADER")
        await self._read_until(follower, action="GET_SHOW_SESSION_DATA")
        self.assertEqual((uuid_a, None), self._live_session_state())

        follower.close()
        ws_a.close()
        ws_x.close()

    @gen_test
    async def test_unconfirmed_leader_cannot_drive_and_expires(self):
        """Leadership adopted without auth can't drive the show, and it is
        released when the provisional window expires (NO_LEADER here).
        """
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)
        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))

        ws_x, _ = await self._refresh_only(uuid_l)
        await ws_x.write_message(
            json.dumps(
                {"OP": "SCRIPT_SCROLL", "DATA": {"current_line": "page_9_line_9"}}
            )
        )
        await asyncio.sleep(0.05)
        self.assertNotIn("SCRIPT_SCROLL", await self._actions(follower))

        await self._fire(provisional_key(uuid_l))
        await self._read_until(follower, action="NO_LEADER")
        await self._read_until(follower, action="GET_SHOW_SESSION_DATA")
        self.assertEqual((None, uuid_l), self._live_session_state())

        follower.close()
        ws_x.close()

    @gen_test
    async def test_adopted_leadership_released_when_auth_fails(self):
        """Leadership adopted by REFRESH_CLIENT is handed on at once if
        AUTHENTICATE fails, and followers are told to re-fetch session data.
        """
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        ws_a, uuid_a = await self._connect_and_auth(self.admin_id)
        follower, _ = await self._connect_and_auth(self.viewer_id)
        self._start_live_session(uuid_l, self.admin_id)
        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))

        ws_x, _ = await self._refresh_only(uuid_l)
        expired = self._token(self.admin_id, expires_delta=timedelta(seconds=-10))
        self.assertEqual("WS_AUTH_ERROR", await self._authenticate(ws_x, expired))

        await self._read_until(ws_a, action="ELECTED_LEADER")
        await self._read_until(follower, action="GET_SHOW_SESSION_DATA")
        self.assertEqual((uuid_a, None), self._live_session_state())
        self.assertFalse(
            self._app.pending_disconnects.is_scheduled(provisional_key(uuid_l))
        )

        follower.close()
        ws_a.close()
        ws_x.close()

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    @gen_test
    async def test_logout_releases_edit_lock_and_leadership(self):
        """Logging out releases the client's edit lock and leadership and says so."""
        ws1, uuid1, observer = await self._editor_and_observer()
        self._start_live_session(uuid1, self.admin_id)

        response = await self._post(
            "/api/v1/auth/logout", {"session_id": uuid1}, self._token(self.admin_id)
        )
        self.assertEqual(200, response.code)

        self.assertEqual((False, False, None), self._session_row(uuid1))
        _, skipped = await self._read_until(observer, action="NO_LEADER")
        self.assertIn("GET_SCRIPT_CONFIG_STATUS", [m.get("ACTION") for m in skipped])
        await self._read_until(observer, action="GET_SHOW_SESSION_DATA")
        self.assertEqual((None, uuid1), self._live_session_state())

        observer.close()
        ws1.close()

    @gen_test
    async def test_logout_ignores_another_users_session(self):
        """Logout can't be used to strip another user's lock."""
        ws1, uuid1, observer = await self._editor_and_observer()

        response = await self._post(
            "/api/v1/auth/logout", {"session_id": uuid1}, self._token(self.viewer_id)
        )
        self.assertEqual(200, response.code)
        self.assertEqual((True, False, self.admin_id), self._session_row(uuid1))

        observer.close()
        ws1.close()

    # ------------------------------------------------------------------
    # REFRESH_CLIENT payload handling
    # ------------------------------------------------------------------

    @gen_test
    async def test_invalid_refresh_payloads_are_ignored(self):
        """``null``, ``""`` and ``123`` leave the connection on its own uuid."""
        ws, placeholder = await self._connect_and_auth(self.admin_id)
        for payload in (None, "", 123):
            await ws.write_message(
                json.dumps({"OP": "REFRESH_CLIENT", "DATA": payload})
            )
        await self._barrier(ws, self.admin_id)

        self.assertIsNotNone(self._session_row(placeholder))
        self.assertIsNotNone(self._app.get_ws(placeholder))
        ws.close()

    @gen_test
    async def test_second_refresh_on_a_connection_is_ignored(self):
        """A repeated REFRESH_CLIENT must not delete the resumed (leader) row."""
        ws_l, uuid_l = await self._connect_and_auth(self.admin_id)
        self._start_live_session(uuid_l, self.admin_id)
        await self._close_and_wait(ws_l, self._app.get_ws(uuid_l))
        ws2 = await self._reload(uuid_l, self.admin_id)

        await ws2.write_message(
            json.dumps({"OP": "REFRESH_CLIENT", "DATA": "some-other-uuid"})
        )
        await self._barrier(ws2, self.admin_id)

        self.assertIsNotNone(self._session_row(uuid_l))
        self.assertIsNone(self._session_row("some-other-uuid"))
        self.assertEqual(uuid_l, self._live_session_state()[0])
        self.assertIsNotNone(self._app.get_ws(uuid_l))
        ws2.close()

    # ------------------------------------------------------------------
    # Collaborative editing room across a reload
    # ------------------------------------------------------------------

    async def _editor_viewer_in_room(self):
        ws_e, uuid_e = await self._connect_and_auth(self.admin_id)
        ws_v, _ = await self._connect_and_auth(self.admin_id)
        await self._become_editor(ws_e, ws_v)
        await self._join_room(ws_e)
        await self._join_room(ws_v)
        room = self._app.room_manager.get_active_room()
        self.assertIsNotNone(room)
        return ws_e, uuid_e, ws_v, room

    @gen_test
    async def test_editor_reload_rejoin_within_grace_keeps_room_open(self):
        """The last editor reloading and rejoining in the window keeps the room.

        Viewers must not get ROOM_CLOSED and the room is not torn down and rebuilt.
        """
        ws_e, uuid_e, ws_v, room = await self._editor_viewer_in_room()

        await self._close_and_wait(ws_e, self._app.get_ws(uuid_e))
        self.assertIs(room, self._app.room_manager.get_active_room())

        ws_e2 = await self._reload(uuid_e, self.admin_id)
        await self._join_room(ws_e2)
        self.assertEqual("editor", room.clients.get(self._app.get_ws(uuid_e)))

        # Expire the (uncancelled) deferred room check.
        await self._fire(room_close_key(room.revision_id))

        self.assertIs(room, self._app.room_manager.get_active_room())
        self.assertNotIn("ROOM_CLOSED", await self._actions(ws_v))

        ws_v.close()
        ws_e2.close()

    @gen_test
    async def test_second_reload_within_window_supersedes_room_close_timer(self):
        """Reloading twice inside the window keeps one room-close timer, pushed back
        to the second departure, so the first departure cannot close the room early.
        """
        ws_e, uuid_e, ws_v, room = await self._editor_viewer_in_room()
        key = room_close_key(room.revision_id)
        registry = self._app.pending_disconnects

        await self._close_and_wait(ws_e, self._app.get_ws(uuid_e))
        first_deadline = registry._timers[key][0].when()

        ws_e2 = await self._reload(uuid_e, self.admin_id)
        await self._join_room(ws_e2)
        await asyncio.sleep(0.05)
        await self._close_and_wait(ws_e2, self._app.get_ws(uuid_e))

        self.assertTrue(registry.is_scheduled(key))
        self.assertGreater(registry._timers[key][0].when(), first_deadline)

        ws_v.close()

    @gen_test(timeout=25)
    async def test_editor_reload_without_rejoin_closes_room_after_grace_real_timer(
        self,
    ):
        """If the reloaded editor never rejoins, the room still closes at expiry.

        Runs on a real (wall-clock) timer.
        """
        self._set_grace(self.SHORT_GRACE)
        ws_e, uuid_e, ws_v, room = await self._editor_viewer_in_room()

        await self._close_and_wait(ws_e, self._app.get_ws(uuid_e))
        ws_e2 = await self._reload(uuid_e, self.admin_id)
        # The editor flag survived, but the page never rejoined the room.
        self.assertTrue(self._session_row(uuid_e)[0])

        await self._read_until(ws_v, action="ROOM_CLOSED", timeout=self.TIMER_WAIT)
        self.assertIsNone(self._app.room_manager.get_active_room())

        ws_v.close()
        ws_e2.close()

    @gen_test
    async def test_deferred_room_close_checkpoints_dirty_room(self):
        """A dirty room closed by the deferred check is checkpointed to a draft."""
        ws_e, uuid_e, ws_v, room = await self._editor_viewer_in_room()
        room._dirty = True

        await self._close_and_wait(ws_e, self._app.get_ws(uuid_e))
        await self._fire(room_close_key(room.revision_id))

        self.assertIsNone(self._app.room_manager.get_active_room())
        with self._app.get_db().sessionmaker() as session:
            draft = session.scalar(
                select(ScriptDraft).where(ScriptDraft.revision_id == self.revision_id)
            )
            self.assertIsNotNone(draft, "the dirty room was not checkpointed")

        ws_v.close()
