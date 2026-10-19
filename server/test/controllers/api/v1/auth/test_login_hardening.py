import asyncio
from unittest import mock

import bcrypt
from sqlalchemy import select
from tornado import escape
from tornado.httpclient import HTTPRequest
from tornado.testing import gen_test

from models.user import User
from registry.named_locks import NamedLockRegistry
from services.login_throttle import LoginThrottle
from services.password_service import PasswordService
from test.conftest import DigiScriptTestCase


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class TestLoginThrottleUnit(DigiScriptTestCase):
    """Behaviour of the in-memory throttle, driven by a fake clock."""

    def setUp(self):
        super().setUp()
        self.clock = FakeClock()
        self.throttle = LoginThrottle(clock=self.clock)

    def test_user_locked_out_after_free_attempts_with_backoff(self):
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS - 1):
            self.throttle.record_failure("1.1.1.1", "alice")
        self.assertEqual(0, self.throttle.retry_after("1.1.1.1", "alice"))

        self.throttle.record_failure("1.1.1.1", "alice")
        first = self.throttle.retry_after("1.1.1.1", "alice")
        self.assertEqual(int(LoginThrottle.BASE_LOCKOUT), first)

        # The lockout expires, and a further failure doubles it.
        self.clock.now += first + 1
        self.assertEqual(0, self.throttle.retry_after("1.1.1.1", "alice"))
        self.throttle.record_failure("1.1.1.1", "alice")
        self.assertEqual(
            int(LoginThrottle.BASE_LOCKOUT * 2),
            self.throttle.retry_after("1.1.1.1", "alice"),
        )

    def test_lockout_is_capped(self):
        for _ in range(100):
            self.throttle.record_failure("1.1.1.1", "alice")
            self.clock.now += LoginThrottle.MAX_LOCKOUT + 1
            # Keep the entry alive: decay is measured from the last failure.
        self.throttle.record_failure("1.1.1.1", "alice")
        self.assertLessEqual(
            self.throttle.retry_after("2.2.2.2", "alice"),
            int(LoginThrottle.MAX_LOCKOUT),
        )

    def test_other_username_unaffected_but_ip_counts_across_usernames(self):
        for i in range(LoginThrottle.IP_FREE_ATTEMPTS):
            self.throttle.record_failure("1.1.1.1", f"user{i}")
        self.assertGreater(self.throttle.retry_after("1.1.1.1", "fresh"), 0)
        self.assertEqual(0, self.throttle.retry_after("9.9.9.9", "fresh"))

    def test_success_clears_username_counter_only(self):
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS):
            self.throttle.record_failure("1.1.1.1", "alice")
        self.assertGreater(self.throttle.retry_after("2.2.2.2", "alice"), 0)
        self.throttle.record_success("alice")
        self.assertEqual(0, self.throttle.retry_after("2.2.2.2", "alice"))

    def test_state_decays(self):
        for _ in range(3):
            self.throttle.record_failure("1.1.1.1", "alice")
        self.clock.now += LoginThrottle.DECAY + 1
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS - 1):
            self.throttle.record_failure("1.1.1.1", "alice")
        # Old failures were forgotten, so we are still under the threshold.
        self.assertEqual(0, self.throttle.retry_after("1.1.1.1", "alice"))

    def test_tables_are_bounded(self):
        with mock.patch.object(LoginThrottle, "MAX_ENTRIES", 50):
            throttle = LoginThrottle(clock=self.clock)
            for i in range(500):
                throttle.record_failure(f"10.0.0.{i}", f"name{i}")
            self.assertLessEqual(len(throttle._users.entries), 50)
            self.assertLessEqual(len(throttle._ips.entries), 50)


class TestLoginHardening(DigiScriptTestCase):
    def setUp(self):
        super().setUp()
        self.clock = FakeClock()
        self._app.login_throttle = LoginThrottle(clock=self.clock)

    def _login(self, username, password):
        return self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": username, "password": password}),
        )

    def _create_admin(self):
        resp = self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )
        self.assertEqual(200, resp.code)

    def test_repeated_failures_get_429_with_retry_after(self):
        self._create_admin()
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS):
            self.assertEqual(401, self._login("admin", "wrongpass1").code)

        resp = self._login("admin", "wrongpass1")
        self.assertEqual(429, resp.code)
        self.assertGreater(int(resp.headers["Retry-After"]), 0)

        # The right password is refused too while locked out.
        self.assertEqual(429, self._login("admin", "adminpass").code)

        # ... and accepted once the lockout has passed.
        self.clock.now += LoginThrottle.BASE_LOCKOUT + 1
        self.assertEqual(200, self._login("admin", "adminpass").code)

    def test_unknown_username_is_throttled_like_a_real_one(self):
        self._create_admin()
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS):
            self.assertEqual(401, self._login("nobody", "wrongpass1").code)
        self.assertEqual(429, self._login("nobody", "wrongpass1").code)

    def test_successful_login_resets_username_counter(self):
        self._create_admin()
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS - 1):
            self._login("admin", "wrongpass1")
        self.assertEqual(200, self._login("admin", "adminpass").code)
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS - 1):
            self.assertEqual(401, self._login("admin", "wrongpass1").code)

    def test_unknown_user_still_runs_a_bcrypt_verification(self):
        self._create_admin()
        with mock.patch.object(
            PasswordService,
            "verify_dummy_password",
            wraps=PasswordService.verify_dummy_password,
        ) as dummy:
            self.assertEqual(401, self._login("nobody", "whatever1").code)
            dummy.assert_called_once()

    def test_dummy_hash_is_a_valid_bcrypt_hash(self):
        self.assertFalse(bcrypt.checkpw(b"nope", PasswordService.DUMMY_HASH.encode()))

    def test_password_minimum_length_is_eight(self):
        resp = self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "1234567", "is_admin": True}
            ),
        )
        self.assertEqual(400, resp.code)
        self.assertIn("at least 8", escape.json_decode(resp.body)["message"])

    def test_temporary_password_has_four_words(self):
        self.assertEqual(
            4, len(PasswordService.generate_temporary_password().split("-"))
        )

    @gen_test
    async def test_concurrent_first_run_creates_only_one_admin_v1(self):
        await self._concurrent_first_run("/api/v1/auth/create")

    @gen_test
    async def test_concurrent_first_run_creates_only_one_admin_v2(self):
        await self._concurrent_first_run("/api/v2/users")

    async def _concurrent_first_run(self, path):
        def make(name):
            return HTTPRequest(
                self.get_url(path),
                method="POST",
                body=escape.json_encode(
                    {"username": name, "password": "adminpass", "is_admin": True}
                ),
            )

        responses = await asyncio.gather(
            *[
                self.http_client.fetch(make(f"admin{i}"), raise_error=False)
                for i in range(4)
            ]
        )
        codes = sorted(r.code for r in responses)
        self.assertEqual([200, 401, 401, 401], codes)
        with self._app.get_db().sessionmaker() as session:
            self.assertEqual(1, len(session.scalars(select(User)).all()))


class TestNamedLockPruning(DigiScriptTestCase):
    @gen_test
    async def test_locks_are_discarded_after_use(self):
        before = set(NamedLockRegistry._locks)
        for i in range(50):
            async with NamedLockRegistry.acquire(f"prune-test-{i}"):
                pass
        self.assertEqual(before, set(NamedLockRegistry._locks))
        self.assertFalse([k for k in NamedLockRegistry._refs if "prune-test" in k])

    @gen_test
    async def test_lock_survives_while_a_waiter_is_queued(self):
        name = "prune-test-contended"
        order = []

        async def worker(tag):
            async with NamedLockRegistry.acquire(name):
                order.append(f"in-{tag}")
                await asyncio.sleep(0.01)
                order.append(f"out-{tag}")

        await asyncio.gather(worker(1), worker(2), worker(3))
        # Strictly serialised: never two inside at once.
        for i in range(0, 6, 2):
            self.assertEqual(order[i][3:], order[i + 1][4:])
        self.assertNotIn(name, NamedLockRegistry._locks)
