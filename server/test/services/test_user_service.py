from unittest.mock import AsyncMock, MagicMock, patch

from tornado.testing import gen_test

from models.session import Session
from models.user import User
from test.conftest import DigiScriptTestCase


class TestUserService(DigiScriptTestCase):
    """Unit tests for UserService"""

    def setUp(self):
        super().setUp()
        self.user_service = self._app.user_service

    @gen_test
    async def test_change_password_success(self):
        """Test that change_password successfully updates user password"""
        # Create a test user
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.commit()
            user_id = user.id

        # Change password
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            await self.user_service.change_password(
                session, user, "new_password_123", invalidate_tokens=False
            )

            # Verify password was changed
            session.refresh(user)
            self.assertNotEqual("old_hash", user.password)
            self.assertFalse(user.requires_password_change)

    @gen_test
    async def test_change_password_sets_requires_password_change_false(self):
        """Test that change_password sets requires_password_change to False"""
        # Create a user that requires password change
        with self._app.get_db().sessionmaker() as session:
            user = User(
                username="testuser",
                password="old_hash",
                requires_password_change=True,
            )
            session.add(user)
            session.commit()
            user_id = user.id

        # Change password
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            await self.user_service.change_password(
                session, user, "new_password_123", invalidate_tokens=False
            )

            # Verify requires_password_change is now False
            session.refresh(user)
            self.assertFalse(user.requires_password_change)

    @gen_test
    async def test_change_password_validates_password_strength(self):
        """Test that change_password rejects weak passwords"""
        # Create a test user
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.commit()
            user_id = user.id

        # Try to change to weak password (< 6 characters)
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            with self.assertRaises(ValueError) as context:
                await self.user_service.change_password(
                    session, user, "short", invalidate_tokens=False
                )

            self.assertIn("at least 6 characters", str(context.exception))

    @gen_test
    async def test_change_password_with_invalidate_tokens(self):
        """Test that change_password can invalidate tokens and force logout"""
        # Create a test user
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.commit()
            user_id = user.id

        # Mock the WebSocket send method
        with patch.object(
            self._app, "ws_send_to_user", new_callable=AsyncMock
        ) as mock_ws_send:
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, user_id)
                await self.user_service.change_password(
                    session, user, "new_password_123", invalidate_tokens=True
                )

                # Verify WebSocket message was sent to log out user
                mock_ws_send.assert_called_once_with(user_id, "NOOP", "USER_LOGOUT", {})

    @gen_test
    async def test_force_logout_all_sessions_sends_websocket_message(self):
        """Test that force_logout_all_sessions sends USER_LOGOUT message"""
        # Create a test user
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.commit()
            user_id = user.id

        # Mock the WebSocket send method
        with patch.object(
            self._app, "ws_send_to_user", new_callable=AsyncMock
        ) as mock_ws_send:
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, user_id)
                await self.user_service.force_logout_all_sessions(session, user)

                # Verify WebSocket message was sent
                mock_ws_send.assert_called_once_with(user_id, "NOOP", "USER_LOGOUT", {})

    @gen_test
    async def test_force_logout_all_sessions_with_active_sessions(self):
        """Every connection on the user's clients is logged out server-side, told
        USER_LOGOUT, and the client's edit lock and leadership are released.
        """
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.flush()
            session.add(
                Session(internal_id="test-session-id", user_id=user.id, is_editor=True)
            )
            session.commit()
            user_id = user.id

        # One connection authenticated as the user, one unauthenticated
        # connection on the same client uuid (e.g. a duplicated tab mid-reload).
        authed = MagicMock(internal_id="test-session-id", current_user_id=user_id)
        authed.write_message = MagicMock(return_value=None)
        unauthed = MagicMock(internal_id="test-session-id", current_user_id=None)
        unauthed.write_message = MagicMock(return_value=None)
        observer = MagicMock(internal_id="someone-else", current_user_id=None)
        observer.write_message = MagicMock(return_value=None)
        self._app.clients[:] = [authed, unauthed, observer]
        try:
            with patch.object(
                self._app, "ws_send_to_user", new_callable=AsyncMock
            ) as mock_ws_send:
                with self._app.get_db().sessionmaker() as session:
                    user = session.get(User, user_id)
                    await self.user_service.force_logout_all_sessions(session, user)

            mock_ws_send.assert_called_once_with(user_id, "NOOP", "USER_LOGOUT", {})
            # The unauthenticated holder isn't reached by ws_send_to_user, so it
            # gets its own USER_LOGOUT.
            sent = [c.args[0] for c in unauthed.write_message.call_args_list]
            self.assertIn({"OP": "NOOP", "DATA": "{}", "ACTION": "USER_LOGOUT"}, sent)
            self.assertIsNone(authed.current_user_id)
            self.assertIsNone(unauthed.current_user_id)
            with self._app.get_db().sessionmaker() as session:
                row = session.get(Session, "test-session-id")
                self.assertFalse(row.is_editor)
            broadcast = [
                c.args[0].get("ACTION") for c in observer.write_message.call_args_list
            ]
            self.assertIn("GET_SCRIPT_CONFIG_STATUS", broadcast)
        finally:
            self._app.clients.clear()

    @gen_test
    async def test_force_logout_all_sessions_without_websocket(self):
        """Test that force_logout_all_sessions handles missing WebSocket gracefully"""
        # Create a test user with a session but no active WebSocket
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.flush()

            ws_session = Session(internal_id="test-session-id", user_id=user.id)
            session.add(ws_session)
            session.commit()
            user_id = user.id

        # No connected WebSocket for the client at all.
        with patch.object(
            self._app, "ws_send_to_user", new_callable=AsyncMock
        ) as mock_ws_send:
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, user_id)

                # Should not raise an error even without active WebSocket
                await self.user_service.force_logout_all_sessions(session, user)

                # Verify WebSocket send was still called
                mock_ws_send.assert_called_once()

    @gen_test
    async def test_change_password_hashes_password(self):
        """Test that change_password properly hashes the new password"""
        # Create a test user
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.commit()
            user_id = user.id

        new_password = "new_password_123"

        # Change password
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            await self.user_service.change_password(
                session, user, new_password, invalidate_tokens=False
            )

            session.refresh(user)

            # Verify password is not stored in plain text
            self.assertNotEqual(new_password, user.password)

            # Verify it's a bcrypt hash (60 chars, starts with $2b$)
            self.assertEqual(60, len(user.password))
            self.assertTrue(
                user.password.startswith("$2b$") or user.password.startswith("$2a$")
            )
