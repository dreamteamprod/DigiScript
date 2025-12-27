from datetime import timedelta
from unittest import TestCase

import pytest

from utils.web.jwt_service import JWTService


class TestJWTService(TestCase):
    def setUp(self):
        self.jwt_service = JWTService(secret="test-secret")

    def test_encode(self):
        token = self.jwt_service.create_access_token({"user_id": 1})
        assert token is not None

    def test_decode(self):
        data = {"user_id": 1}
        token = self.jwt_service.create_access_token(data)
        decoded = self.jwt_service.decode_access_token(token)
        assert decoded["user_id"] == data["user_id"]

    def test_expired_token(self):
        token = self.jwt_service.create_access_token(
            {"user_id": 1}, expires_delta=timedelta(minutes=-5)
        )
        decoded = self.jwt_service.decode_access_token(token)
        assert decoded is None

    def test_invalid_algorithm(self):
        with pytest.raises(ValueError, match="Unsupported JWT algorithm"):
            JWTService(secret="123", jwt_algorithm="unsupported-algo")
