import unittest
from unittest import mock

from services.login_throttle import LoginThrottle


class FakeClock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


class TestLoginThrottle(unittest.TestCase):
    """Behaviour of the in-memory login throttle, driven by a fake clock."""

    def setUp(self):
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
        self.throttle.record_failure("1.1.1.1", "alice")
        self.assertLessEqual(
            self.throttle.retry_after("2.2.2.2", "alice"),
            int(LoginThrottle.MAX_LOCKOUT),
        )

    def test_ip_counts_across_usernames(self):
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
        self.assertEqual(0, self.throttle.retry_after("1.1.1.1", "alice"))

    def test_tables_are_bounded(self):
        with mock.patch.object(LoginThrottle, "MAX_ENTRIES", 50):
            throttle = LoginThrottle(clock=self.clock)
            for i in range(500):
                throttle.record_failure(f"10.0.0.{i}", f"name{i}")
            self.assertLessEqual(len(throttle._users.entries), 50)
            self.assertLessEqual(len(throttle._ips.entries), 50)

    def test_reset_forgets_everything(self):
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS):
            self.throttle.record_failure("1.1.1.1", "alice")
        self.throttle.reset()
        self.assertEqual(0, self.throttle.retry_after("1.1.1.1", "alice"))
