import asyncio
import hashlib
from unittest import TestCase, mock

import bcrypt
from tornado import escape
from tornado.testing import gen_test

from models.user import User
from test.conftest import DigiScriptTestCase
from test.helpers.auth_fixtures import craft_token, make_user
from utils.web.api_keys import ApiKeyRateLimited, ApiKeyService


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


class TestApiKeyLegacyUpgradeRaces(DigiScriptTestCase):
    def _legacy_user(self, key="legacy-secret-value", username="legacy") -> int:
        user_id = make_user(self._app, username)
        with self._app.get_db().sessionmaker() as session:
            session.get(User, user_id).api_token = bcrypt.hashpw(
                key.encode(), bcrypt.gensalt(4)
            ).decode()
            session.commit()
        self._app.jwt_service.api_keys.invalidate()
        return user_id

    @gen_test
    async def test_concurrent_burst_from_one_address_is_bounded(self):
        self._legacy_user()
        service = self._app.jwt_service.api_keys
        with self._app.get_db().sessionmaker() as session:
            results = await asyncio.gather(
                *[
                    service.authenticate(session, f"bad-{i}", "10.0.0.1")
                    for i in range(service._max_failed + 4)
                ],
                return_exceptions=True,
            )
        limited = [r for r in results if isinstance(r, ApiKeyRateLimited)]
        self.assertEqual(4, len(limited))

    @gen_test
    async def test_limited_address_stays_limited_when_others_fill_tracking(self):
        self._legacy_user()
        service = ApiKeyService(max_failed_scans=1, max_tracked_addresses=2)
        with self._app.get_db().sessionmaker() as session:
            self.assertIsNone(await service.authenticate(session, "bad", "10.0.0.1"))
            self.assertIsNone(await service.authenticate(session, "bad", "10.0.0.2"))
            self.assertIsNone(await service.authenticate(session, "bad", "10.0.0.3"))
            # 10.0.0.3 evicted the oldest active address, not the limit it just hit
            with self.assertRaises(ApiKeyRateLimited):
                await service.authenticate(session, "bad", "10.0.0.3")

    @gen_test
    async def test_key_regenerated_during_legacy_check_is_not_revived(self):
        user_id = self._legacy_user()
        service = self._app.jwt_service.api_keys
        replacement = hashlib.sha256(b"regenerated").hexdigest()

        async def regenerate_then_match(executor, func, api_key, stored, uid):
            # Runs on the loop thread (the in-memory test DB is per-thread).
            with self._app.get_db().sessionmaker() as other:
                other.get(User, uid).api_token = replacement
                other.commit()
            return True

        loop = asyncio.get_running_loop()
        with self._app.get_db().sessionmaker() as session:
            with mock.patch.object(loop, "run_in_executor", regenerate_then_match):
                user = await service.authenticate(
                    session, "legacy-secret-value", "10.0.0.1"
                )
        self.assertIsNone(user)
        with self._app.get_db().sessionmaker() as session:
            self.assertEqual(replacement, session.get(User, user_id).api_token)

    @gen_test
    async def test_malformed_legacy_hash_is_rejected_and_logged(self):
        user_id = make_user(self._app)
        with self._app.get_db().sessionmaker() as session:
            session.get(User, user_id).api_token = "$2b$not-a-real-hash"
            session.commit()
        service = self._app.jwt_service.api_keys
        service.invalidate()
        with self._app.get_db().sessionmaker() as session:
            with self.assertLogs(level="WARNING") as logs:
                self.assertIsNone(
                    await service.authenticate(session, "anything", "10.0.0.1")
                )
        self.assertTrue(any(f"user {user_id}" in line for line in logs.output))

    @gen_test
    async def test_upgrade_succeeds_when_reservation_aged_out_during_scan(self):
        self._legacy_user()
        now = [0.0]
        service = ApiKeyService(window_seconds=10, clock=lambda: now[0])

        async def slow_match(executor, func, api_key, stored, uid):
            now[0] += 100  # scan outlasts the window
            service._prune("10.0.0.1", now[0])
            return True

        loop = asyncio.get_running_loop()
        with self._app.get_db().sessionmaker() as session:
            with mock.patch.object(loop, "run_in_executor", slow_match):
                user = await service.authenticate(
                    session, "legacy-secret-value", "10.0.0.1"
                )
        self.assertIsNotNone(user)
