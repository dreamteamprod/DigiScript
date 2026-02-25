"""Integration tests for WebSocket controller query patterns.

These tests connect to the WebSocket endpoint and send messages to trigger
the query patterns in ws_controller.py, following our endpoint-based testing approach.
"""

import json
from unittest.mock import AsyncMock

import pycrdt
from sqlalchemy import select
from tornado.testing import gen_test
from tornado.websocket import websocket_connect

from models.script import Script, ScriptRevision
from models.script_draft import ScriptDraft
from models.session import Session, ShowSession
from models.show import Show, ShowScriptType
from models.user import User
from test.conftest import DigiScriptTestCase
from utils.script_room_manager import ScriptRoom


class TestWSControllerIntegration(DigiScriptTestCase):
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

    # ------------------------------------------------------------------
    # REQUEST_SCRIPT_EDIT tests
    # ------------------------------------------------------------------

    @gen_test
    async def test_request_script_edit_no_editors(self):
        """Admin requests edit when no editors exist — should succeed."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))

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

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))

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

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))

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

        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))

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
        self._app.room_manager._rooms[self.revision_id] = room

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
        del self._app.room_manager._rooms[self.revision_id]
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
    # JOIN_SCRIPT_ROOM — role based on edit state, not just RBAC
    # ------------------------------------------------------------------

    @gen_test
    async def test_join_script_room_viewer_when_not_editing(self):
        """Admin who hasn't entered edit mode joins room as viewer."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Join room WITHOUT requesting edit first
        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )

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

        ws.close()

    @gen_test
    async def test_request_edit_upgrades_room_role(self):
        """Admin joins room as viewer, then requests edit — role upgrades to editor."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Join room first (as viewer, since not yet editing)
        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws.read_message()  # YJS_SYNC
        members_msg = await ws.read_message()
        members_data = json.loads(members_msg)
        self.assertEqual("viewer", members_data["DATA"]["members"][0]["role"])
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Now request edit — should upgrade role
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))

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
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        # Join room (as editor)
        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
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
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        # Join room (as editor)
        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Make a modification to mark the doc dirty
        room = self._app.room_manager.get_room(self.revision_id)
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
        self.assertIsNone(self._app.room_manager.get_room(self.revision_id))

        ws.close()

    @gen_test
    async def test_join_script_room_editor_when_editing(self):
        """Admin who entered edit mode joins room as editor."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode first
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # Consume GET_SCRIPT_CONFIG_STATUS

        # Now join room
        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )

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
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Verify room exists
        self.assertIsNotNone(self._app.room_manager.get_room(self.revision_id))

        # Stop editing (last editor)
        await ws.write_message(json.dumps({"OP": "STOP_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # ROOM_MEMBERS

        # Should receive ROOM_CLOSED
        room_closed_msg = await ws.read_message()
        room_closed_data = json.loads(room_closed_msg)
        self.assertEqual("NOOP", room_closed_data["OP"])
        self.assertEqual("ROOM_CLOSED", room_closed_data["ACTION"])
        self.assertEqual(
            f"draft_{self.revision_id}", room_closed_data["DATA"]["room_id"]
        )

        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        # Room should be evicted
        self.assertIsNone(self._app.room_manager.get_room(self.revision_id))

        ws.close()

    @gen_test
    async def test_stop_edit_keeps_room_when_other_editors(self):
        """Two editors in room, one stops — room stays open, no ROOM_CLOSED."""
        ws1, uuid1 = await self._connect_and_auth(self.admin_id)
        ws2, uuid2 = await self._connect_and_auth(self.admin_id)

        # Both enter edit mode
        await ws1.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws1.read_message()  # GET_SCRIPT_CONFIG_STATUS for ws1
        await ws2.read_message()  # GET_SCRIPT_CONFIG_STATUS for ws2 (broadcast)

        await ws2.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws1.read_message()  # GET_SCRIPT_CONFIG_STATUS for ws1 (broadcast)
        await ws2.read_message()  # GET_SCRIPT_CONFIG_STATUS for ws2

        # Both join room
        await ws1.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws1.read_message()  # YJS_SYNC
        await ws1.read_message()  # ROOM_MEMBERS
        await ws1.read_message()  # GET_SCRIPT_CONFIG_STATUS from join
        await ws2.read_message()  # GET_SCRIPT_CONFIG_STATUS from join (broadcast)

        await ws2.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
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
        room = self._app.room_manager.get_room(self.revision_id)
        self.assertIsNotNone(room)
        self.assertTrue(room.has_editors)

        ws1.close()
        ws2.close()

    @gen_test
    async def test_disconnect_closes_room_when_last_editor(self):
        """Editor disconnects — remaining viewer receives ROOM_CLOSED."""
        ws_editor, _ = await self._connect_and_auth(self.admin_id)
        ws_viewer, _ = await self._connect_and_auth(self.admin_id)

        # Editor enters edit mode
        await ws_editor.write_message(
            json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}})
        )
        await ws_editor.read_message()  # GET_SCRIPT_CONFIG_STATUS
        await ws_viewer.read_message()  # GET_SCRIPT_CONFIG_STATUS broadcast

        # Both join room
        await ws_editor.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws_editor.read_message()  # YJS_SYNC
        await ws_editor.read_message()  # ROOM_MEMBERS
        await ws_editor.read_message()  # GET_SCRIPT_CONFIG_STATUS from join
        await ws_viewer.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        await ws_viewer.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
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
        self.assertIsNone(self._app.room_manager.get_room(self.revision_id))

        ws_viewer.close()

    # ------------------------------------------------------------------
    # SAVE_SCRIPT_DRAFT tests
    # ------------------------------------------------------------------

    @gen_test
    async def test_save_script_draft_success(self):
        """SAVE_SCRIPT_DRAFT dispatches to save_room; editor receives SCRIPT_SAVED."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Send save request. save_draft always updates meta.last_saved_at in the Y.Doc,
        # so save_room always broadcasts YJS_UPDATE first, then SCRIPT_SAVED.
        await ws.write_message(json.dumps({"OP": "SAVE_SCRIPT_DRAFT", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("YJS_UPDATE", response_data["ACTION"])

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("SCRIPT_SAVED", response_data["ACTION"])
        self.assertIn("last_saved_at", response_data["DATA"])

        ws.close()

    @gen_test
    async def test_save_script_draft_error_sent_to_requester(self):
        """If save_draft raises, the requesting editor receives SAVE_ERROR."""
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Patch the room's save_draft to raise
        room = self._app.room_manager.get_room(self.revision_id)

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
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        self.assertIsNotNone(self._app.room_manager.get_room(self.revision_id))

        await ws.write_message(json.dumps({"OP": "DISCARD_SCRIPT_DRAFT", "DATA": {}}))

        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("ROOM_CLOSED", response_data["ACTION"])
        self.assertEqual(f"draft_{self.revision_id}", response_data["DATA"]["room_id"])

        # Room should be evicted after discard
        self.assertIsNone(self._app.room_manager.get_room(self.revision_id))

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
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Confirm the room starts clean (no Y.Doc mutations yet)
        room = self._app.room_manager.get_room(self.revision_id)
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
        self.assertIsNone(self._app.room_manager.get_room(self.revision_id))

        ws.close()

    @gen_test
    async def test_stop_edit_dirty_room_checkpoints_before_close(self):
        """Last editor stops editing with a dirty room — checkpoint IS written.

        Any Y.Doc mutation sets _dirty = True. STOP_SCRIPT_EDIT should
        checkpoint (creating a ScriptDraft) before closing the room.
        """
        ws, uuid = await self._connect_and_auth(self.admin_id)

        # Enter edit mode and join room
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS

        await ws.write_message(
            json.dumps(
                {"OP": "JOIN_SCRIPT_ROOM", "DATA": {"revision_id": self.revision_id}}
            )
        )
        await ws.read_message()  # YJS_SYNC
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from join

        # Mutate the Y.Doc to mark it dirty
        room = self._app.room_manager.get_room(self.revision_id)
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
        self.assertIsNone(self._app.room_manager.get_room(self.revision_id))
