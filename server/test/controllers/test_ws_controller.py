"""Integration tests for WebSocket controller query patterns.

These tests connect to the WebSocket endpoint and send messages to trigger
the query patterns in ws_controller.py, following our endpoint-based testing approach.
"""

import json

from sqlalchemy import select
from tornado.testing import gen_test
from tornado.websocket import websocket_connect

from models.session import Session, ShowSession
from models.show import Show
from models.user import User
from test.utils import DigiScriptTestCase


class TestWSControllerIntegration(DigiScriptTestCase):
    """Test WebSocket controller query patterns via WebSocket connections."""

    def setUp(self):
        super().setUp()
        # Create a test user for authentication
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="hashed")
            session.add(user)
            session.flush()
            self.user_id = user.id
            session.commit()

    @gen_test
    async def test_request_script_edit_no_editors(self):
        """Test REQUEST_SCRIPT_EDIT when no editors exist.

        This tests the query at lines 288-290 in controllers/ws_controller.py:
        session.scalars(select(Session).where(Session.is_editor)).all()

        When a user requests script edit permission and no editors exist,
        the query should return empty list and permission should be granted.
        """
        # Connect to WebSocket
        ws_url = self.get_url("/api/v1/ws").replace("http://", "ws://")
        ws = await websocket_connect(ws_url)

        # Receive initial messages (SET_UUID and GET_SETTINGS)
        msg1 = await ws.read_message()
        msg1_data = json.loads(msg1)
        self.assertEqual("SET_UUID", msg1_data["OP"])

        msg2 = await ws.read_message()
        msg2_data = json.loads(msg2)
        self.assertEqual("NOOP", msg2_data["OP"])
        self.assertEqual("GET_SETTINGS", msg2_data["ACTION"])

        # Send REQUEST_SCRIPT_EDIT message
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))

        # Verify we get GET_SCRIPT_CONFIG_STATUS (indicating success)
        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response_data["ACTION"])

        # Verify the session was marked as editor
        with self._app.get_db().sessionmaker() as db_session:
            editors = db_session.scalars(select(Session).where(Session.is_editor)).all()
            self.assertEqual(1, len(editors))
            self.assertTrue(editors[0].is_editor)

        ws.close()

    @gen_test
    async def test_request_script_edit_with_existing_editor(self):
        """Test REQUEST_SCRIPT_EDIT when an editor already exists.

        This tests the query at lines 288-290 when an editor session exists.
        The query should find the existing editor and deny permission.
        """
        # Create an existing editor session
        with self._app.get_db().sessionmaker() as session:
            editor_session = Session(
                internal_id="existing-editor", user_id=self.user_id, is_editor=True
            )
            session.add(editor_session)
            session.commit()

        # Connect to WebSocket
        ws_url = self.get_url("/api/v1/ws").replace("http://", "ws://")
        ws = await websocket_connect(ws_url)

        # Receive initial messages
        msg1 = await ws.read_message()
        msg2 = await ws.read_message()

        # Send REQUEST_SCRIPT_EDIT message
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": {}}))

        # Verify we get REQUEST_EDIT_FAILURE (indicating denial)
        response = await ws.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("REQUEST_EDIT_FAILURE", response_data["ACTION"])

        # Verify the session was NOT marked as editor
        internal_id = json.loads(msg1)["DATA"]
        with self._app.get_db().sessionmaker() as session:
            new_session = session.get(Session, internal_id)
            self.assertFalse(new_session.is_editor)

        ws.close()

    @gen_test
    async def test_websocket_close_elects_leader(self):
        """Test leader election when WebSocket closes during live session.

        This tests the query at lines 118-122 in controllers/ws_controller.py:
        session.scalars(
            select(Session).where(Session.user_id == live_session.user_id)
        ).first()

        When a WebSocket controlling a live session closes, the system should
        find another session for the same user to elect as new leader.
        """
        # Create a show with a live session
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            show_id = show.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show_id)

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
            # The live_session relationship is auto-populated via client_internal_id
            show_session = ShowSession(
                show_id=show_id,
                user_id=self.user_id,
                client_internal_id=ws1_uuid,
            )
            session.add(show_session)
            session.flush()

            show = session.get(Show, show_id)
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
            show = session.get(Show, show_id)
            show_session = session.get(ShowSession, show.current_session_id)
            self.assertEqual(ws2_uuid, show_session.client_internal_id)

        ws2.close()

    @gen_test
    async def test_websocket_close_no_next_leader(self):
        """Test leader election when no other session exists for user.

        This tests the query at lines 118-122 when the query returns None.
        When a WebSocket closes and there's no other session for the user,
        all clients should receive NO_LEADER message.
        """
        # Create a show with a live session
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            show_id = show.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show_id)

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

            # Create show session - live_session relationship auto-populated
            show_session = ShowSession(
                show_id=show_id,
                user_id=self.user_id,
                client_internal_id=ws1_uuid,
            )
            session.add(show_session)
            session.flush()

            show = session.get(Show, show_id)
            show.current_session_id = show_session.id
            session.commit()

        # Close the WebSocket - should trigger NO_LEADER since no other session exists
        ws1.close()

        # Verify observer receives NO_LEADER message
        response = await ws_observer.read_message()
        response_data = json.loads(response)
        self.assertEqual("NOOP", response_data["OP"])
        self.assertEqual("NO_LEADER", response_data["ACTION"])

        ws_observer.close()
