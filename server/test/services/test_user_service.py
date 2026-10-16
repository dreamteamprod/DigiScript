from unittest.mock import MagicMock, patch

from tornado.testing import gen_test

from models.session import Session
from models.user import User
from test.conftest import DigiScriptTestCase


LOGOUT = {"OP": "NOOP", "DATA": "{}", "ACTION": "USER_LOGOUT"}


class TestUserService(DigiScriptTestCase):
    """Unit tests for UserService"""

    def setUp(self):
        super().setUp()
        self.user_service = self._app.user_service

    @staticmethod
    def _fake_client(internal_id, user_id):
        """A stand-in WebSocket handler that records what it is sent."""
        client = MagicMock(internal_id=internal_id, current_user_id=user_id)
        client.write_message = MagicMock(return_value=None)
        return client

    @staticmethod
    def _sent(client):
        return [c.args[0] for c in client.write_message.call_args_list]

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

        tab = self._fake_client("tab", user_id)
        self._app.clients[:] = [tab]
        try:
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, user_id)
                await self.user_service.change_password(
                    session, user, "new_password_123", invalidate_tokens=True
                )
            # The user's connection was logged out and told so.
            self.assertEqual([LOGOUT], self._sent(tab))
            self.assertIsNone(tab.current_user_id)
        finally:
            self._app.clients.clear()

    @gen_test
    async def test_force_logout_all_sessions_sends_websocket_message(self):
        """Test that force_logout_all_sessions sends USER_LOGOUT message"""
        # Create a test user
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.commit()
            user_id = user.id

        tab = self._fake_client("tab", user_id)
        self._app.clients[:] = [tab]
        try:
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, user_id)
                await self.user_service.force_logout_all_sessions(session, user)
            self.assertEqual([LOGOUT], self._sent(tab))
        finally:
            self._app.clients.clear()

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
        authed = self._fake_client("test-session-id", user_id)
        unauthed = self._fake_client("test-session-id", None)
        observer = self._fake_client("someone-else", None)
        self._app.clients[:] = [authed, unauthed, observer]
        try:
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, user_id)
                await self.user_service.force_logout_all_sessions(session, user)

            # Each affected connection gets exactly one USER_LOGOUT, including
            # the unauthenticated holder of the user's client.
            self.assertEqual(1, self._sent(authed).count(LOGOUT))
            self.assertEqual(1, self._sent(unauthed).count(LOGOUT))
            self.assertNotIn(LOGOUT, self._sent(observer))
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

        # No connected WebSocket for the client at all: must not raise.
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            await self.user_service.force_logout_all_sessions(session, user)

    @gen_test
    async def test_force_logout_leaves_other_users_holder_alone(self):
        """A connection authenticated as a *different* user that holds one of
        the target user's client ids is not the target's connection: it keeps
        its login and gets no USER_LOGOUT.
        """
        with self._app.get_db().sessionmaker() as session:
            target = User(username="target", password="old_hash")
            other = User(username="other", password="old_hash")
            session.add_all([target, other])
            session.flush()
            session.add(Session(internal_id="target-client", user_id=target.id))
            session.commit()
            target_id, other_id = target.id, other.id

        other_on_target_client = self._fake_client("target-client", other_id)
        self._app.clients[:] = [other_on_target_client]
        try:
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, target_id)
                await self.user_service.force_logout_all_sessions(session, user)
            self.assertEqual(other_id, other_on_target_client.current_user_id)
            self.assertNotIn(LOGOUT, self._sent(other_on_target_client))
        finally:
            self._app.clients.clear()

    @gen_test
    async def test_force_logout_never_raises_and_falls_back_to_deadline(self):
        """If releasing a client fails, force-logout still logs everything out,
        sends USER_LOGOUT, schedules the client's grace deadline, and returns
        normally (it runs after a committed password change).
        """
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.flush()
            session.add(Session(internal_id="c1", user_id=user.id, is_editor=True))
            session.commit()
            user_id = user.id

        tab = self._fake_client("c1", user_id)
        self._app.clients[:] = [tab]
        try:
            with patch(
                "services.user_service.release_session_privileges",
                side_effect=RuntimeError("database is locked"),
            ):
                with self._app.get_db().sessionmaker() as session:
                    user = session.get(User, user_id)
                    await self.user_service.force_logout_all_sessions(session, user)
            self.assertIsNone(tab.current_user_id)
            self.assertEqual([LOGOUT], self._sent(tab))
            self.assertTrue(self._app.pending_disconnects.is_pending("c1"))
        finally:
            self._app.clients.clear()

    @gen_test
    async def test_force_logout_survives_a_failing_client_lookup(self):
        """Even if the user's clients can't be listed, its authenticated
        connections are still logged out, and nothing raises.
        """
        with self._app.get_db().sessionmaker() as session:
            user = User(username="testuser", password="old_hash")
            session.add(user)
            session.commit()
            user_id = user.id

        tab = self._fake_client("tab", user_id)
        self._app.clients[:] = [tab]
        try:
            broken = MagicMock()
            broken.scalars.side_effect = RuntimeError("database is locked")
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, user_id)
            await self.user_service.force_logout_all_sessions(broken, user)
            self.assertIsNone(tab.current_user_id)
            self.assertEqual([LOGOUT], self._sent(tab))
        finally:
            self._app.clients.clear()

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
