import unittest
from unittest import mock

from services.login_throttle import LoginThrottle, _Tracker


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
        for _ in range(40):
            self.throttle.record_failure("1.1.1.1", "alice")
        self.assertEqual(
            int(LoginThrottle.MAX_LOCKOUT),
            self.throttle.retry_after("2.2.2.2", "alice"),
        )

    def test_counter_does_not_reset_when_a_maximum_lockout_ends(self):
        for _ in range(40):
            self.throttle.record_failure("1.1.1.1", "alice")
        # Retrying the moment the lockout ends must keep the lockout at its cap
        # rather than hand out fresh free attempts.
        self.clock.now += LoginThrottle.MAX_LOCKOUT
        self.assertEqual(0, self.throttle.retry_after("1.1.1.1", "alice"))
        self.throttle.record_failure("1.1.1.1", "alice")
        self.assertEqual(
            int(LoginThrottle.MAX_LOCKOUT),
            self.throttle.retry_after("1.1.1.1", "alice"),
        )

    def test_begin_attempt_reserves_so_a_burst_is_bounded(self):
        allowed = sum(
            1 for _ in range(50) if self.throttle.begin_attempt("1.1.1.1", "alice") == 0
        )
        self.assertEqual(LoginThrottle.USER_FREE_ATTEMPTS, allowed)

    def test_begin_attempt_refusal_is_not_counted(self):
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS):
            self.throttle.begin_attempt("1.1.1.1", "alice")
        first = self.throttle.begin_attempt("1.1.1.1", "alice")
        for _ in range(10):
            self.throttle.begin_attempt("1.1.1.1", "alice")
        self.assertEqual(first, self.throttle.begin_attempt("1.1.1.1", "alice"))

    def test_successful_attempt_is_refunded_on_the_address(self):
        for _ in range(LoginThrottle.IP_FREE_ATTEMPTS * 3):
            self.assertEqual(0, self.throttle.begin_attempt("1.1.1.1", "alice"))
            self.throttle.record_success("1.1.1.1", "alice")

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            _Tracker(0, 30.0, 900.0, 900.0, 10)
        with self.assertRaises(ValueError):
            _Tracker(5, 30.0, 900.0, 900.0, 0)

    def test_ip_counts_across_usernames(self):
        for i in range(LoginThrottle.IP_FREE_ATTEMPTS):
            self.throttle.record_failure("1.1.1.1", f"user{i}")
        self.assertGreater(self.throttle.retry_after("1.1.1.1", "fresh"), 0)
        self.assertEqual(0, self.throttle.retry_after("9.9.9.9", "fresh"))

    def test_success_clears_username_counter_only(self):
        for _ in range(LoginThrottle.USER_FREE_ATTEMPTS):
            self.throttle.record_failure("1.1.1.1", "alice")
        self.assertGreater(self.throttle.retry_after("2.2.2.2", "alice"), 0)
        self.throttle.record_success("2.2.2.2", "alice")
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
