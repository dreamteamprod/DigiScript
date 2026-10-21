import asyncio
import hashlib
import hmac
import secrets
import time
from collections import deque
from typing import Callable, Deque, Dict, Optional

import bcrypt
from sqlalchemy import select, update

from digi_server.logger import get_logger
from models.user import User


class ApiKeyRateLimited(Exception):
    """Raised when an address has used up its allowance of legacy key scans."""


class ApiKeyService:
    """
    API key generation and verification.

    Keys are random secrets; only ``sha256(key)`` (hex) is stored in
    ``User.api_token``, so authentication is a single indexed lookup.

    Keys created before this scheme are bcrypt hashes (``$2...``). They keep
    working: when a presented key matches no SHA-256 row, the remaining legacy
    rows are bcrypt-checked and a match is rewritten to the SHA-256 form, so
    each legacy key is scanned only until its first use. That scan is the one
    expensive path, so it is only run while legacy rows exist and is limited to
    a few failed scans per remote address per window.
    """

    def __init__(
        self,
        max_failed_scans: int = 5,
        window_seconds: float = 60.0,
        max_tracked_addresses: int = 10000,
        clock: Callable[[], float] = time.monotonic,
    ):
        """
        :param max_failed_scans: Failed legacy scans allowed per address per window.
        :param window_seconds: Length of the sliding window.
        :param max_tracked_addresses: Bound on remembered addresses.
        :param clock: Monotonic time source (injectable for tests).
        """
        self._max_failed = max_failed_scans
        self._window = window_seconds
        self._max_tracked = max_tracked_addresses
        self._clock = clock
        self._failures: Dict[str, Deque[float]] = {}
        self._has_legacy: Optional[bool] = None

    @staticmethod
    def hash_key(api_key: str) -> str:
        """SHA-256 hex digest of a key (keys are high entropy, so no KDF)."""
        return hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    @classmethod
    def generate(cls) -> "tuple[str, str]":
        """
        :returns: ``(plaintext_key, stored_hash)``; only the hash is stored.
        """
        key = secrets.token_urlsafe(32)
        return key, cls.hash_key(key)

    def invalidate(self) -> None:
        """Forget the cached "legacy rows exist" flag (call when api_token changes)."""
        self._has_legacy = None

    def _legacy_exists(self, session) -> bool:
        if self._has_legacy is None:
            self._has_legacy = (
                session.scalars(
                    select(User.id).where(User.api_token.like("$2%")).limit(1)
                ).first()
                is not None
            )
        return self._has_legacy

    def _prune(self, address: str, now: float) -> Deque[float]:
        attempts = self._failures.get(address)
        if attempts is None:
            if len(self._failures) >= self._max_tracked:
                # Drop addresses with no failures left in the window first, so
                # flooding with new addresses cannot reset an active limit; only
                # if every tracked address is active is the oldest one evicted.
                idle = [
                    ip
                    for ip, hits in self._failures.items()
                    if not hits or now - hits[-1] >= self._window
                ]
                for ip in idle or [next(iter(self._failures))]:
                    del self._failures[ip]
            attempts = self._failures[address] = deque()
        while attempts and now - attempts[0] >= self._window:
            attempts.popleft()
        return attempts

    async def authenticate(
        self, session, api_key: str, remote_ip: str
    ) -> Optional[User]:
        """
        Resolve an API key to its user.

        :param session: Open SQLAlchemy session (committed when a key is upgraded).
        :param api_key: The presented key.
        :param remote_ip: Client address, used to limit legacy scans.
        :returns: The user, or None if the key is not valid.
        :raises ApiKeyRateLimited: If the address has exhausted its legacy scans.
        """
        digest = self.hash_key(api_key)
        user = session.scalars(select(User).where(User.api_token == digest)).first()
        # The lookup already matched on the digest; the constant-time compare is
        # belt-and-braces so the match never depends on database collation.
        if user and hmac.compare_digest(user.api_token.encode(), digest.encode()):
            return user

        if not self._legacy_exists(session):
            return None

        now = self._clock()
        attempts = self._prune(remote_ip, now)
        if len(attempts) >= self._max_failed:
            raise ApiKeyRateLimited()
        # Reserve the slot before scanning so a concurrent burst from one address
        # is bounded; it is released again if the scan finds a match.
        attempts.append(now)

        legacy_users = session.scalars(
            select(User).where(User.api_token.like("$2%"))
        ).all()
        loop = asyncio.get_running_loop()
        for candidate in legacy_users:
            stored = candidate.api_token
            matches = await loop.run_in_executor(
                None, _check_bcrypt, api_key, stored, candidate.id
            )
            if not matches:
                continue
            # Conditional upgrade: if the key was revoked or regenerated while the
            # (slow) bcrypt check ran, the row no longer holds ``stored`` and the
            # stale match must not revive it.
            result = session.execute(
                update(User)
                .where(User.id == candidate.id, User.api_token == stored)
                .values(api_token=digest)
            )
            session.commit()
            self.invalidate()
            if result.rowcount != 1:
                continue
            attempts.remove(now)
            session.refresh(candidate)
            return candidate

        return None


def _check_bcrypt(api_key: str, stored: str, user_id: int) -> bool:
    try:
        return bcrypt.checkpw(api_key.encode("utf-8"), stored.encode("utf-8"))
    except ValueError:
        get_logger().warning(f"Malformed legacy api_token hash for user {user_id}")
        return False
