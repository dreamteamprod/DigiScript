from datetime import datetime, timedelta, timezone
from unittest import TestCase

import pytest
from jwt import PyJWT
from sqlalchemy import select
from tornado.testing import gen_test

from digi_server.settings import SettingsObject
from models.user import User
from test.conftest import DigiScriptTestCase
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


class TestJWTServiceTokenAge(TestCase):
    def setUp(self):
        self.jwt_service = JWTService(secret="test-secret")

    def test_token_within_lifetime_accepted(self):
        token = self.jwt_service.create_access_token({"user_id": 1})
        payload = self.jwt_service.decode_access_token(token)
        assert self.jwt_service.validate_token_age(payload, max_lifetime_hours=24)

    def test_token_exceeding_lifetime_rejected(self):
        old_iat = (datetime.now(tz=timezone.utc) - timedelta(hours=25)).timestamp()
        payload = {"user_id": 1, "iat": old_iat}
        assert not self.jwt_service.validate_token_age(payload, max_lifetime_hours=24)

    def test_missing_iat_rejected(self):
        assert not self.jwt_service.validate_token_age(
            {"user_id": 1}, max_lifetime_hours=24
        )

    def test_token_just_within_boundary_accepted(self):
        near_boundary_iat = (
            datetime.now(tz=timezone.utc) - timedelta(hours=23, minutes=59)
        ).timestamp()
        payload = {"user_id": 1, "iat": near_boundary_iat}
        assert self.jwt_service.validate_token_age(payload, max_lifetime_hours=24)

    def test_no_application_and_no_override_skips_check(self):
        # JWTService without application should skip age check (returns True)
        very_old_iat = datetime(2000, 1, 1, tzinfo=timezone.utc).timestamp()
        payload = {"user_id": 1, "iat": very_old_iat}
        assert self.jwt_service.validate_token_age(payload)

    def test_create_access_token_uses_default_expiry_without_application(self):
        token = self.jwt_service.create_access_token({"user_id": 1})
        assert self.jwt_service.decode_access_token(token) is not None

    def test_explicit_expires_delta_overrides_default(self):
        token = self.jwt_service.create_access_token(
            {"user_id": 1}, expires_delta=timedelta(minutes=-5)
        )
        assert self.jwt_service.decode_access_token(token) is None


class TestJWTTokenAgeIntegration(DigiScriptTestCase):
    def _craft_old_token(self, user_id: int, token_version: int, age_hours: int) -> str:
        now = datetime.now(tz=timezone.utc)
        payload = {
            "user_id": user_id,
            "token_version": token_version,
            "iat": now - timedelta(hours=age_hours),
            "exp": now + timedelta(hours=24),
            "jti": "test-old-token",
        }
        return PyJWT().encode(
            payload,
            self._app.jwt_service.get_secret(),
            algorithm="HS256",
        )

    def _get_user(self, username: str) -> User:
        with self._app.get_db().sessionmaker() as session:
            return session.scalars(
                select(User).where(User.username == username)
            ).first()

    @gen_test
    async def test_validate_token_age_reads_from_settings(self):
        await self._app.digi_settings.set("jwt_token_lifetime_hours", 1)
        old_iat = (datetime.now(tz=timezone.utc) - timedelta(hours=2)).timestamp()
        payload = {"user_id": 1, "iat": old_iat}
        assert not self._app.jwt_service.validate_token_age(payload)

    @gen_test
    async def test_validate_token_age_fresh_token_passes_with_reduced_lifetime(self):
        await self._app.digi_settings.set("jwt_token_lifetime_hours", 1)
        fresh_iat = datetime.now(tz=timezone.utc).timestamp()
        payload = {"user_id": 1, "iat": fresh_iat}
        assert self._app.jwt_service.validate_token_age(payload)

    def test_old_token_rejected_at_http_level(self):
        self._create_and_login_admin()
        user = self._get_user("admin")

        self._app.digi_settings.settings["jwt_token_lifetime_hours"].set_value(
            1, spawn_callbacks=False
        )

        old_token = self._craft_old_token(user.id, user.token_version, age_hours=2)
        response = self.fetch(
            "/api/v1/auth", headers={"Authorization": f"Bearer {old_token}"}
        )
        self.assertEqual(401, response.code)

    def test_fresh_token_accepted_after_lifetime_reduction(self):
        fresh_token = self._create_and_login_admin()
        self._app.digi_settings.settings["jwt_token_lifetime_hours"].set_value(
            1, spawn_callbacks=False
        )
        response = self.fetch(
            "/api/v1/auth", headers={"Authorization": f"Bearer {fresh_token}"}
        )
        self.assertEqual(200, response.code)

    def test_create_access_token_uses_configured_lifetime(self):
        self._create_and_login_admin()
        user = self._get_user("admin")
        self._app.digi_settings.settings["jwt_token_lifetime_hours"].set_value(
            6, spawn_callbacks=False
        )
        token = self._app.jwt_service.create_access_token({"user_id": user.id})
        payload = self._app.jwt_service.decode_access_token(token)
        assert payload is not None
        issued_at = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        expiry = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        delta_hours = (expiry - issued_at).total_seconds() / 3600
        self.assertAlmostEqual(delta_hours, 6, delta=0.1)


class TestChoiceLabelsValidation(TestCase):
    def test_choice_labels_length_mismatch_raises(self):
        with pytest.raises(RuntimeError, match="same length"):
            SettingsObject(
                "test_key",
                int,
                1,
                choice_options=[1, 2],
                choice_labels=["one"],
            )

    def test_choice_labels_non_string_raises(self):
        with pytest.raises(RuntimeError, match="must be strings"):
            SettingsObject(
                "test_key",
                int,
                1,
                choice_options=[1],
                choice_labels=[42],
            )

    def test_choice_labels_without_choice_options_raises(self):
        with pytest.raises(RuntimeError, match="requires choice_options"):
            SettingsObject(
                "test_key",
                int,
                1,
                choice_labels=["label"],
            )

    def test_choice_labels_appear_in_as_json(self):
        setting = SettingsObject(
            "test_key",
            int,
            1,
            choice_options=[1, 2],
            choice_labels=["one", "two"],
        )
        setting.set_to_default()
        json_repr = setting.as_json()
        assert json_repr["choice_labels"] == ["one", "two"]

    def test_no_choice_labels_returns_none_in_as_json(self):
        setting = SettingsObject("test_key", int, 1, choice_options=[1, 2])
        setting.set_to_default()
        json_repr = setting.as_json()
        assert json_repr["choice_labels"] is None
