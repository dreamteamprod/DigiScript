from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import tornado.locks
from jwt import PyJWS, PyJWT, PyJWTError
from sqlalchemy import delete, select

from models.settings import SystemSettings
from models.user import RevokedToken, User
from utils.web.api_keys import ApiKeyService


# Reasons returned by JWTService.validate_access_token.
TOKEN_REVOKED = "revoked"
TOKEN_INVALID = "invalid"
TOKEN_EXPIRED = "expired"
TOKEN_SESSION_EXPIRED = "session_expired"
TOKEN_VERSION_INVALID = "version_invalid"

# Absolute cap on how long a login session may be kept alive by refreshing.
DEFAULT_MAX_SESSION_LIFETIME = timedelta(days=30)


class JWTService:
    def __init__(
        self,
        application=None,
        secret=None,
        jwt_algorithm: str = "HS256",
        default_expiry: timedelta = timedelta(days=1),
        max_session_lifetime: timedelta = DEFAULT_MAX_SESSION_LIFETIME,
    ):
        """
        Initialize JWT service with either application instance or direct secret
        """
        self.application = application
        self._jwt = PyJWT()
        self._jws = PyJWS()
        if jwt_algorithm not in self._jws.get_algorithms():
            raise ValueError(
                f"Unsupported JWT algorithm: {jwt_algorithm}. Supported algorithms: {self._jws.get_algorithms()}"
            )
        self._secret = secret
        self._jwt_algorithm = jwt_algorithm
        self._default_expiry = default_expiry
        self._max_session_lifetime = max_session_lifetime
        self.api_keys = ApiKeyService()
        # jti -> expiry (unix seconds). Write-through cache of the
        # ``revoked_token`` table (memory only when there is no application).
        self._revoked_tokens: Dict[str, int] = {}
        self._revoked_loaded = False
        self._revoked_token_lock = tornado.locks.Lock()

    def _load_revoked(self) -> None:
        """Load persisted revocations into the cache on first use (lock held)."""
        if self._revoked_loaded:
            return
        self._revoked_loaded = True
        if not self.application:
            return
        now = int(datetime.now(tz=timezone.utc).timestamp())
        with self.application.get_db().sessionmaker() as session:
            session.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))
            session.commit()
            for row in session.scalars(select(RevokedToken)).all():
                self._revoked_tokens[row.jti] = row.expires_at

    def _unverified_claims(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            return self._jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
                algorithms=[self._jwt_algorithm],
            )
        except Exception:
            return None

    async def revoke_token(self, token: str):
        """
        Revoke a token by its ``jti`` until its natural expiry.

        Revocations are persisted so they survive a restart, and expired ones
        are pruned on every call (an expired token is rejected by signature
        validation anyway).

        :param token: The JWT to revoke.
        """
        payload = self._unverified_claims(token)
        jti = payload.get("jti") if payload else None
        if not jti:
            return
        expiry = int(payload.get("exp", 0))
        now = int(datetime.now(tz=timezone.utc).timestamp())
        async with self._revoked_token_lock:
            self._load_revoked()
            self._revoked_tokens = {
                k: v for k, v in self._revoked_tokens.items() if v >= now
            }
            if expiry < now:
                return
            self._revoked_tokens[jti] = expiry
            if self.application:
                with self.application.get_db().sessionmaker() as session:
                    session.execute(
                        delete(RevokedToken).where(RevokedToken.expires_at < now)
                    )
                    session.merge(RevokedToken(jti=jti, expires_at=expiry))
                    session.commit()

    async def is_token_revoked(self, token: str) -> bool:
        """
        Check whether a token has been revoked.

        :param token: The JWT to check.
        :returns: True if the token's ``jti`` is on the (unexpired) revocation list.
        """
        payload = self._unverified_claims(token)
        jti = payload.get("jti") if payload else None
        if not jti:
            return False
        async with self._revoked_token_lock:
            self._load_revoked()
            expiry = self._revoked_tokens.get(jti)
            if expiry is None:
                return False
            if expiry < int(datetime.now(tz=timezone.utc).timestamp()):
                self._revoked_tokens.pop(jti, None)
                return False
            return True

    async def validate_access_token(
        self, token: str
    ) -> "tuple[Optional[Dict[str, Any]], Optional[str]]":
        """
        Single validation routine shared by REST and WebSocket authentication.

        Checks, in order: revocation, signature/expiry, presence of ``user_id``,
        per-token age, absolute session age, and the user's ``token_version``.

        :param token: The JWT access token.
        :returns: ``(payload, None)`` when valid, otherwise ``(None, reason)``
            where reason is one of the ``TOKEN_*`` constants.
        """
        if await self.is_token_revoked(token):
            return None, TOKEN_REVOKED
        payload = self.decode_access_token(token)
        if not payload or "user_id" not in payload:
            return None, TOKEN_INVALID
        if not self.validate_token_age(payload):
            return None, TOKEN_EXPIRED
        if not self.validate_session_age(payload):
            return None, TOKEN_SESSION_EXPIRED
        if not self.is_token_version_valid(payload):
            return None, TOKEN_VERSION_INVALID
        return payload, None

    def get_secret(self):
        """
        Get JWT secret from database or use provided secret
        """
        if self._secret:
            return self._secret

        if not self.application:
            raise RuntimeError("No application or secret provided to JWT service")

        with self.application.get_db().sessionmaker() as session:
            jwt_secret = session.scalars(
                select(SystemSettings).where(SystemSettings.key == "jwt_secret")
            ).first()

            if not jwt_secret:
                raise RuntimeError("JWT secret not initialized in database")

            return jwt_secret.value

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT access token with user token_version
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(tz=timezone.utc) + expires_delta
        elif self.application:
            lifetime_hours = self.application.digi_settings.settings[
                "jwt_token_lifetime_hours"
            ].get_value()
            expire = datetime.now(tz=timezone.utc) + timedelta(hours=lifetime_hours)
        else:
            expire = datetime.now(tz=timezone.utc) + self._default_expiry

        # Add token version if user_id is provided
        if "user_id" in data and self.application:
            with self.application.get_db().sessionmaker() as session:
                user = session.get(User, data["user_id"])
                if user:
                    to_encode["token_version"] = user.token_version

        now = datetime.now(tz=timezone.utc)
        # ``auth_time`` is when the user actually authenticated. Refreshes carry
        # the original value forward so the session cap cannot be reset.
        to_encode.setdefault("auth_time", int(now.timestamp()))
        to_encode.update({"exp": expire, "iat": now, "jti": str(uuid4())})
        encoded_jwt = self._jwt.encode(
            to_encode, self.get_secret(), algorithm=self._jwt_algorithm
        )

        return encoded_jwt

    def decode_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token
        """
        try:
            payload = self._jwt.decode(
                token,
                self.get_secret(),
                options={"require": ["exp"]},
                algorithms=[self._jwt_algorithm],
            )
            return payload
        except PyJWTError:
            return None

    def is_token_version_valid(self, payload: Dict[str, Any]) -> bool:
        """
        Validate that token version matches current user token version

        :param payload: Decoded JWT payload
        :type payload: Dict[str, Any]
        :return: True if token version is valid, False otherwise
        :rtype: bool
        """
        user_id = payload.get("user_id")
        token_version = payload.get("token_version")

        if user_id is None or token_version is None:
            # Old tokens without version or missing user_id
            return False

        with self.application.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            if not user:
                return False

            return user.token_version == token_version

    def validate_token_age(
        self, payload: Dict[str, Any], max_lifetime_hours: Optional[int] = None
    ) -> bool:
        """
        Check that a token was issued within the configured maximum lifetime.

        When ``max_lifetime_hours`` is not provided, reads the configured value from
        application settings. If no application is set (standalone or test use),
        the check is skipped and ``True`` is returned.

        :param payload: Decoded JWT payload containing an ``iat`` (issued-at) claim.
        :type payload: Dict[str, Any]
        :param max_lifetime_hours: Override for the maximum allowed token age in hours.
            If ``None``, reads from the ``jwt_token_lifetime_hours`` application setting.
        :type max_lifetime_hours: Optional[int]
        :return: ``True`` if the token is within the allowed age, ``False`` otherwise.
        :rtype: bool
        """
        iat = payload.get("iat")
        if iat is None:
            return False

        if max_lifetime_hours is None:
            if not self.application:
                return True
            max_lifetime_hours = self.application.digi_settings.settings[
                "jwt_token_lifetime_hours"
            ].get_value()

        issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
        age = datetime.now(tz=timezone.utc) - issued_at
        return age <= timedelta(hours=max_lifetime_hours)

    def validate_session_age(self, payload: Dict[str, Any]) -> bool:
        """
        Check the absolute session cap using the ``auth_time`` claim.

        Tokens issued before ``auth_time`` existed fall back to ``iat``.

        :param payload: Decoded JWT payload.
        :returns: True if the original login is within the maximum session lifetime.
        """
        auth_time = payload.get("auth_time", payload.get("iat"))
        if auth_time is None:
            return False
        started = datetime.fromtimestamp(auth_time, tz=timezone.utc)
        return datetime.now(tz=timezone.utc) - started <= self._max_session_lifetime

    @staticmethod
    def get_token_from_authorization_header(auth_header: str) -> Optional[str]:
        """
        Extract token from Authorization header
        """
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        return auth_header[7:]
