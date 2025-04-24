from datetime import timedelta

from utils.web.jwt_utils import create_access_token, decode_access_token


def test_encode():
    token = create_access_token({"user_id": 1})
    assert token is not None


def test_decode():
    data = {"user_id": 1}
    token = create_access_token(data)
    decoded = decode_access_token(token)
    assert decoded["user_id"] == data["user_id"]


def test_expired_token():
    token = create_access_token({"user_id": 1}, expires_delta=timedelta(minutes=-5))
    decoded = decode_access_token(token)
    assert decoded is None
