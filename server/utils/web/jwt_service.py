from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

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
        headers = self._jws.get_unverified_header(token)
        expiry = headers.get("exp", -1)
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
        else:
            expire = datetime.now(tz=timezone.utc) + self._default_expiry

        # Add token version if user_id is provided
        if "user_id" in data and self.application:
            with self.application.get_db().sessionmaker() as session:
                user = session.get(User, data["user_id"])
                if user:
                    to_encode["token_version"] = user.token_version

        to_encode.update({"exp": expire, "iat": datetime.now(tz=timezone.utc)})
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

    @staticmethod
    def get_token_from_authorization_header(auth_header: str) -> Optional[str]:
        """
        Extract token from Authorization header
        """
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        return auth_header[7:]
