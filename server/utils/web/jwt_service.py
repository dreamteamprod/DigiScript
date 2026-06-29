from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

import tornado.locks
from jwt import PyJWS, PyJWT, PyJWTError
from sqlalchemy import select

from models.settings import SystemSettings
from models.user import User


class JWTService:
    def __init__(
        self,
        application=None,
        secret=None,
        jwt_algorithm: str = "HS256",
        default_expiry: timedelta = timedelta(days=1),
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
        self._revoked_tokens: Dict[str, int] = {}
        self._revoked_token_lock = tornado.locks.Lock()

    async def revoke_token(self, token: str):
        try:
            payload = self._jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
                algorithms=[self._jwt_algorithm],
            )
            expiry = payload.get("exp", -1)
        except Exception:
            expiry = -1
        async with self._revoked_token_lock:
            self._revoked_tokens[token] = expiry

    async def is_token_revoked(self, token: str):
        async with self._revoked_token_lock:
            if token in self._revoked_tokens:
                expiry = self._revoked_tokens[token]
                if expiry != -1:
                    expiry_time = datetime.fromtimestamp(expiry, tz=timezone.utc)
                    current_time = datetime.now(tz=timezone.utc)
                    if current_time > expiry_time:
                        self._revoked_tokens.pop(token)
                return True
            return False

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

        to_encode.update(
            {"exp": expire, "iat": datetime.now(tz=timezone.utc), "jti": str(uuid4())}
        )
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

    @staticmethod
    def get_token_from_authorization_header(auth_header: str) -> Optional[str]:
        """
        Extract token from Authorization header
        """
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        return auth_header[7:]
