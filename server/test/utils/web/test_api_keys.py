import hashlib
from unittest import TestCase, mock

import bcrypt
from tornado import escape

from models.user import User
from test.conftest import DigiScriptTestCase
from test.helpers.auth_fixtures import craft_token, make_user
from utils.web.api_keys import ApiKeyService


class TestApiKeyService(TestCase):
    def test_generate_returns_key_and_its_sha256(self):
        key, stored = ApiKeyService.generate()
        self.assertEqual(hashlib.sha256(key.encode()).hexdigest(), stored)

    def test_failures_expire_after_window_and_tracking_is_bounded(self):
        service = ApiKeyService(
            max_failed_scans=2,
            window_seconds=10,
            max_tracked_addresses=3,
            clock=lambda: 0.0,
        )
        service._prune("a", 0.0).extend([0.0, 1.0])
        self.assertEqual(2, len(service._prune("a", 5.0)))
        self.assertEqual(1, len(service._prune("a", 10.5)))
        for ip in ("b", "c", "d", "e"):
            service._prune(ip, 0.0)
        self.assertLessEqual(len(service._failures), 3)


class TestApiKeyAuthentication(DigiScriptTestCase):
    def _generate(self, user_id: int) -> str:
        response = self.fetch(
            "/api/v1/auth/api-token/generate",
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {craft_token(self._app, user_id)}"},
        )
        self.assertEqual(200, response.code)
        return escape.json_decode(response.body)["api_token"]

    def _whoami(self, key: str):
        return self.fetch("/api/v1/auth", headers={"X-API-Key": key})

    def _set_legacy(self, user_id: int, key: str) -> None:
        hashed = bcrypt.hashpw(key.encode(), bcrypt.gensalt(4)).decode()
        with self._app.get_db().sessionmaker() as session:
            session.get(User, user_id).api_token = hashed
            session.commit()
        self._app.jwt_service.api_keys.invalidate()

    def _stored(self, user_id: int):
        with self._app.get_db().sessionmaker() as session:
            return session.get(User, user_id).api_token

    def test_legacy_key_authenticates_and_is_upgraded_in_place(self):
        user_id = make_user(self._app)
        self._set_legacy(user_id, "legacy-secret-value")
        self.assertEqual(200, self._whoami("legacy-secret-value").code)
        self.assertEqual(
            hashlib.sha256(b"legacy-secret-value").hexdigest(), self._stored(user_id)
        )
        with mock.patch("bcrypt.checkpw") as checkpw:
            self.assertEqual(200, self._whoami("legacy-secret-value").code)
            checkpw.assert_not_called()

    def test_wrong_key_does_not_run_bcrypt_without_legacy_rows(self):
        key = self._generate(make_user(self._app))
        with mock.patch("bcrypt.checkpw") as checkpw:
            self.assertEqual(401, self._whoami("wrong").code)
            self.assertEqual(401, self._whoami(key + "x").code)
            checkpw.assert_not_called()

    def test_stored_hash_is_not_usable_as_key(self):
        user_id = make_user(self._app)
        self._generate(user_id)
        self.assertEqual(401, self._whoami(self._stored(user_id)).code)

    def test_legacy_scan_is_rate_limited_per_address(self):
        user_id = make_user(self._app)
        self._set_legacy(user_id, "legacy-secret-value")
        now = [0.0]
        service = self._app.jwt_service.api_keys
        service._clock = lambda: now[0]
        for _ in range(service._max_failed):
            self.assertEqual(401, self._whoami("bad").code)
        # Over the limit: no more bcrypt scans, even for the right key.
        with mock.patch("bcrypt.checkpw") as checkpw:
            self.assertEqual(429, self._whoami("legacy-secret-value").code)
            checkpw.assert_not_called()
        now[0] += service._window + 1
        self.assertEqual(200, self._whoami("legacy-secret-value").code)

    def test_fast_path_unaffected_by_rate_limit(self):
        key = self._generate(make_user(self._app))
        self._set_legacy(make_user(self._app, "legacy", is_admin=False), "old-key")
        service = self._app.jwt_service.api_keys
        for _ in range(service._max_failed + 2):
            self._whoami("bad")
        self.assertEqual(200, self._whoami(key).code)
