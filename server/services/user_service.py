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
        requires_password_change: bool = False,
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
        :param requires_password_change: Whether the user must change the new
            password at next login (e.g. an admin-issued temporary password)
        :type requires_password_change: bool
        :raises ValueError: If password validation fails
        """
        is_valid, error_msg = PasswordService.validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(error_msg)

        hashed = await PasswordService.hash_password(new_password)

        user.password = hashed
        user.requires_password_change = requires_password_change

        if invalidate_tokens:
            # Increment token version to invalidate all existing JWTs
            user.token_version += 1

        # Commit before the force-logout fan-out: the password and token
        # invalidation are then durable first, and this session holds no
        # uncommitted write while the release writes through its own
        # connections (which would otherwise wait on SQLite's lock and stall
        # the event loop, then fail with "database is locked").
        session.commit()

        if force_logout_sessions:
            # Force logout all WebSocket sessions. The password change has
            # already landed, so a failure here must not fail the request.
            try:
                await self.force_logout_all_sessions(session, user)
            except Exception:
                get_logger().exception(
                    f"Password change for user {user.id}: forced logout failed; "
                    f"falling back to grace deadlines for its clients"
                )
                self._fallback_logout(user.id)

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

    def _fallback_logout(self, user_id: int) -> None:
        """Best-effort logout when :meth:`force_logout_all_sessions` failed.

        Marks the user's authenticated connections logged out (so nothing can
        use their privileges) and starts the grace deadline of each of the
        user's clients, which releases its lock and leadership. Never raises.

        :param user_id: The user being logged out.
        """
        try:
            for ws_session in self.application.get_all_ws(user_id):
                ws_session.current_user_id = None
            with self.application.get_db().sessionmaker() as fresh:
                client_ids = fresh.scalars(
                    select(Session.internal_id).where(Session.user_id == user_id)
                ).all()
            for client_id in client_ids:
                schedule_disconnect_deadline(self.application, client_id)
        except Exception:
            get_logger().exception(
                f"Fallback logout of user {user_id} failed; its locks and "
                f"leadership are released when its connections close"
            )

    async def force_logout_all_sessions(self, session, user: User) -> None:
        """
        Force logout user from all active sessions via WebSocket.

        Process:
        1. Snapshot every connection authenticated as the user, plus any
           unauthenticated connection using one of the user's client uuids, and
           mark them all logged out on the server straight away, rather than
           waiting for each client's REST logout (which usually fails with 401
           after a token_version bump).
        2. Send each of them USER_LOGOUT (best effort, never raises).
        3. Release each client's edit/cut lock, collaborative-room editor role
           and live-show leadership, with the usual broadcasts (NO_LEADER or
           ELECTED_LEADER).

        :param session: SQLAlchemy session
        :param user: User model instance
        :type user: User
        """
        # Nothing below may raise into the caller: change_password calls this
        # after the password change has committed, and the admin must still get
        # the temporary password back. Sends use safe_write (never raises), and
        # each database step is guarded with a deadline fallback.
        logout_message = {"OP": "NOOP", "DATA": "{}", "ACTION": "USER_LOGOUT"}

        lookup_failed = False
        try:
            client_ids = session.scalars(
                select(Session.internal_id).where(Session.user_id == user.id)
            ).all()
        except Exception:
            # Fall back to the clients of the connections known to be this
            # user's. This must run before the loop below clears
            # current_user_id, which is what get_all_ws matches on.
            lookup_failed = True
            client_ids = sorted(
                {
                    ws.internal_id
                    for ws in self.application.get_all_ws(user.id)
                    if getattr(ws, "internal_id", None)
                }
            )
            get_logger().exception(
                f"Forced logout of user {user.id}: could not list its clients; "
                f"logging out its connected clients {client_ids} and releasing "
                f"them at their grace deadlines"
            )

        # Snapshot and mark every affected connection logged out first, before
        # sending or releasing anything, so an election never picks a tab of
        # this user that is about to be logged out, and last_client_internal_id
        # keeps the original leader's client.
        affected = list(self.application.get_all_ws(user.id))
        for client_id in client_ids:
            # Every connection using the uuid (e.g. a duplicated tab). A holder
            # authenticated as someone else is not this user's connection
            # (reconcile moves such connections to their own uuid anyway).
            for ws_session in holders(self.application, client_id):
                if ws_session.current_user_id in (None, user.id) and not any(
                    ws_session is seen for seen in affected
                ):
                    affected.append(ws_session)
        for ws_session in affected:
            ws_session.current_user_id = None
        for ws_session in affected:
            safe_write(ws_session, logout_message)

        for client_id in client_ids:
            if lookup_failed:
                # The database just failed to answer; don't try to write to it
                # now. finalise_disconnect releases a row held only by
                # unauthenticated connections when the deadline expires.
                schedule_disconnect_deadline(self.application, client_id)
                continue
            try:
                release_session_privileges(self.application, client_id, "forced logout")
            except Exception:
                get_logger().exception(
                    f"Forced logout of user {user.id}: could not release client "
                    f"{client_id} now; releasing it at its grace deadline"
                )
                schedule_disconnect_deadline(self.application, client_id)
