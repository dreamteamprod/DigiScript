"""Helpers for tests that need users and hand-crafted JWTs."""

from datetime import datetime, timedelta, timezone

from jwt import PyJWT

from models.user import User


def make_user(app, username="admin", is_admin=True) -> int:
    """Create a user directly in the database and return its id."""
    with app.get_db().sessionmaker() as session:
        user = User(username=username, password="hashed", is_admin=is_admin)
        session.add(user)
        session.commit()
        return user.id


def craft_token(app, user_id: int, **overrides) -> str:
    """
    Sign a JWT for ``user_id`` with the app secret.

    Claims default to a fresh, valid token carrying the user's current
    ``token_version``; ``overrides`` replace individual claims.
    """
    now = datetime.now(tz=timezone.utc)
    with app.get_db().sessionmaker() as session:
        version = session.get(User, user_id).token_version
    payload = {
        "user_id": user_id,
        "token_version": version,
        "iat": now,
        "auth_time": int(now.timestamp()),
        "exp": now + timedelta(hours=1),
        "jti": "crafted-jti",
    }
    payload.update(overrides)
    return PyJWT().encode(payload, app.jwt_service.get_secret())


def bump_token_version(app, user_id: int) -> None:
    """Invalidate every existing token for the user."""
    with app.get_db().sessionmaker() as session:
        session.get(User, user_id).token_version += 1
        session.commit()
