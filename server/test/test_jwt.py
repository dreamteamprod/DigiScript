from datetime import timedelta

from utils.web.jwt_service import JWTService

jwt_service = JWTService(secret="test-secret")


def test_encode():
    token = jwt_service.create_access_token({"user_id": 1})
    assert token is not None


def test_decode():
    data = {"user_id": 1}
    token = jwt_service.create_access_token(data)
    decoded = jwt_service.decode_access_token(token)
    assert decoded["user_id"] == data["user_id"]


def test_expired_token():
    token = jwt_service.create_access_token(
        {"user_id": 1}, expires_delta=timedelta(minutes=-5)
    )
    decoded = jwt_service.decode_access_token(token)
    assert decoded is None
