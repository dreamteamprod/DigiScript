"""User service for user management operations"""

from sqlalchemy import select
from tornado import gen

from models.session import Session
from models.user import User
from services.password_service import PasswordService


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
        1. Send USER_LOGOUT WebSocket message to all user sessions
        2. Wait for sessions to clear (with retry loop)
        3. Manually send logout to any remaining sessions
           Best-effort - some sessions may not receive message if offline

        :param session: SQLAlchemy session
        :param user: User model instance
        :type user: User
        """
        await self.application.ws_send_to_user(user.id, "NOOP", "USER_LOGOUT", {})

        session_logout_attempts = 0
        user_sessions = session.scalars(
            select(Session).where(Session.user_id == user.id)
        ).all()

        while user_sessions and session_logout_attempts < 5:
            for user_session in user_sessions:
                ws_session = self.application.get_ws(user_session.internal_id)
                if ws_session:
                    await ws_session.write_message(
                        {"OP": "NOOP", "DATA": "{}", "ACTION": "USER_LOGOUT"}
                    )
                    ws_session.current_user_id = None

            await gen.sleep(0.2)
            user_sessions = session.scalars(
                select(Session).where(Session.user_id == user.id)
            ).all()
            session_logout_attempts += 1
