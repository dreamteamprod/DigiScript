from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
import tornado.locks

from models.settings import SystemSettings


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
        self._secret = secret
        self._jwt_algorithm = jwt_algorithm
        self._default_expiry = default_expiry
        self._revoked_tokens: Dict[str, int] = {}
        self._revoked_token_lock = tornado.locks.Lock()

    async def revoke_token(self, token: str):
        headers = jwt.get_unverified_header(token)
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
            jwt_secret = (
                session.query(SystemSettings)
                .filter(SystemSettings.key == "jwt_secret")
                .first()
            )

            if not jwt_secret:
                raise RuntimeError("JWT secret not initialized in database")

            return jwt_secret.value

    def create_access_token(
        self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a new JWT access token
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(tz=timezone.utc) + expires_delta
        else:
            expire = datetime.now(tz=timezone.utc) + self._default_expiry

        to_encode.update({"exp": expire, "iat": datetime.now(tz=timezone.utc)})
        encoded_jwt = jwt.encode(
            to_encode, self.get_secret(), algorithm=self._jwt_algorithm
        )

        return encoded_jwt

    def decode_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token
        """
        try:
            payload = jwt.decode(
                token,
                self.get_secret(),
                options={"require": ["exp"]},
                algorithms=[self._jwt_algorithm],
            )
            return payload
        except jwt.PyJWTError:
            return None

    @staticmethod
    def get_token_from_authorization_header(auth_header: str) -> Optional[str]:
        """
        Extract token from Authorization header
        """
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        return auth_header[7:]
