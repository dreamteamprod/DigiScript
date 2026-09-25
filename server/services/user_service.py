"""User service for user management operations"""

from sqlalchemy import select

from digi_server.logger import get_logger
from models.session import Session
from models.user import User
from services.password_service import PasswordService
from utils.web.ws_session_lifecycle import (
    holders,
    release_session_privileges,
    safe_write,
    schedule_disconnect_deadline,
)


class UserService:
    """Service for user-level operations"""

    def __init__(self, application):
        """
        Initialize UserService.

        :param application: Tornado application instance
        """
        self.application = application

    async def change_password(
        self,
        session,
        user: User,
        new_password: str,
        invalidate_tokens: bool = True,
        force_logout_sessions: bool = True,
    ) -> None:
        """
        Change user's password and optionally invalidate all sessions.

        :param session: SQLAlchemy session
        :param user: User model instance
        :type user: User
        :param new_password: New password (plaintext)
        :type new_password: str
        :param invalidate_tokens: If True, increment token_version to invalidate JWTs
        :type invalidate_tokens: bool
        :param force_logout_sessions: If True, broadcast logout to all sessions
        :type force_logout_sessions: bool
        :raises ValueError: If password validation fails
        """
        is_valid, error_msg = PasswordService.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)

        hashed = await PasswordService.hash_password(new_password)

        user.password = hashed
        user.requires_password_change = False

        if invalidate_tokens:
            # Increment token version to invalidate all existing JWTs
            user.token_version += 1

        if force_logout_sessions:
            # Force logout all WebSocket sessions
            await self.force_logout_all_sessions(session, user)

        session.commit()

    async def refresh_token_all_sessions(self, user: User, new_token: str) -> None:
        """
        Broadcast new JWT token to all user's active sessions for seamless re-auth.

        Sends TOKEN_REFRESH WebSocket message to all user sessions with the new token.
        Each session can then update its stored auth token without interruption.

        :param user: User model instance
        :type user: User
        :param new_token: New JWT access token
        :type new_token: str
        """
        await self.application.ws_send_to_user(
            user.id,
            "NOOP",
            "TOKEN_REFRESH",
            {"access_token": new_token, "token_type": "bearer"},
        )

    async def force_logout_all_sessions(self, session, user: User) -> None:
        """
        Force logout user from all active sessions via WebSocket.

        Process:
        1. Send USER_LOGOUT to every connection authenticated as the user, and to
           any other connection using one of the user's client uuids.
        2. Mark all of those connections logged out on the server straight
           away, rather than waiting for each client's REST logout (which
           usually fails with 401 after a token_version bump).
        3. Release each client's edit/cut lock, collaborative-room editor role
           and live-show leadership, with the usual broadcasts (NO_LEADER or
           ELECTED_LEADER).

        :param session: SQLAlchemy session
        :param user: User model instance
        :type user: User
        """
        await self.application.ws_send_to_user(user.id, "NOOP", "USER_LOGOUT", {})
        logout_message = {"OP": "NOOP", "DATA": "{}", "ACTION": "USER_LOGOUT"}

        client_ids = session.scalars(
            select(Session.internal_id).where(Session.user_id == user.id)
        ).all()
        for client_id in client_ids:
            # Every connection using the uuid (e.g. a duplicated tab).
            for ws_session in holders(self.application, client_id):
                if ws_session.current_user_id != user.id:
                    # Not reached by ws_send_to_user above.
                    safe_write(ws_session, logout_message)
                ws_session.current_user_id = None
            try:
                release_session_privileges(self.application, client_id, "forced logout")
            except Exception:
                get_logger().exception(
                    f"Forced logout of user {user.id}: could not release client "
                    f"{client_id} now; releasing it at its grace deadline"
                )
                schedule_disconnect_deadline(self.application, client_id)
        # Any other connection still authenticated as this user.
        for ws_session in self.application.get_all_ws(user.id):
            ws_session.current_user_id = None
