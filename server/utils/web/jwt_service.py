from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from tornado_sqlalchemy import SessionMixin

from models.settings import SystemSettings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class JWTService:
    def __init__(self, application=None, secret=None):
        """
        Initialize JWT service with either application instance or direct secret
        """
        self.application = application
        self._secret = secret
        
    def get_secret(self):
        """
        Get JWT secret from database or use provided secret
        """
        if self._secret:
            return self._secret
            
        if not self.application:
            raise RuntimeError("No application or secret provided to JWT service")
            
        with self.application.session_maker() as session:
            jwt_secret = session.query(SystemSettings).filter(
                SystemSettings.key == "jwt_secret"
            ).first()
            
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
            expire = datetime.now(tz=timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, self.get_secret(), algorithm=JWT_ALGORITHM
        )
        
        return encoded_jwt
        
    def decode_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token
        """
        try:
            payload = jwt.decode(
                token, self.get_secret(), algorithms=[JWT_ALGORITHM]
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
