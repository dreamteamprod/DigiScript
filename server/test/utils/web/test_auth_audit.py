import unittest
from unittest.mock import patch

from prometheus_client import REGISTRY

from utils.web.auth_audit import (
    EVENTS,
    RESULTS,
    audit,
    auth_events_total,
    sanitise,
)


class TestSanitise(unittest.TestCase):
    def test_strips_control_characters(self):
        self.assertEqual("ab c", sanitise("a\r\nb\x00 \x1bc"))

    def test_truncates(self):
        self.assertEqual(64, len(sanitise("x" * 500)))

    def test_non_string(self):
        self.assertEqual("12", sanitise(12))


class TestAudit(unittest.TestCase):
    def _count(self, event, result):
        return (
            REGISTRY.get_sample_value(
                "digiscript_auth_events_total", {"event": event, "result": result}
            )
            or 0.0
        )

    def test_success_is_info_with_extra(self):
        before = self._count("login", "success")
        with self.assertLogs("DigiScript.Audit", "INFO") as logs:
            audit("login", "success", username="alice", user_id=3, remote_ip="1.2.3.4")
        record = logs.records[0]
        self.assertEqual("INFO", record.levelname)
        self.assertEqual(
            'AUDIT login success username="alice" user_id=3 ip=1.2.3.4',
            record.getMessage(),
        )
        self.assertEqual("alice", record.username)
        self.assertEqual(3, record.user_id)
        self.assertEqual("1.2.3.4", record.remote_ip)
        self.assertEqual(before + 1, self._count("login", "success"))

    def test_failure_is_warning_with_detail(self):
        with self.assertLogs("DigiScript.Audit", "WARNING") as logs:
            audit("login", "failure", username="bob", detail="reason=bad_password")
        self.assertEqual("WARNING", logs.records[0].levelname)
        self.assertTrue(logs.output[0].endswith("reason=bad_password"))

    def test_unknown_event_or_result_is_logged_not_raised_or_counted(self):
        series_before = len(list(auth_events_total.collect()[0].samples))
        with self.assertLogs("DigiScript.Audit", "ERROR") as logs:
            audit("bogus", "success")
            audit("login", "maybe")
        self.assertEqual(2, len(logs.output))
        self.assertEqual(
            series_before, len(list(auth_events_total.collect()[0].samples))
        )

    def test_internal_failure_is_swallowed_and_logged(self):
        with patch("utils.web.auth_audit._emit", side_effect=RuntimeError("boom")):
            with self.assertLogs("DigiScript.Audit", "ERROR") as logs:
                audit("login", "success", username="alice")
        self.assertIsNotNone(logs.records[0].exc_info)

    def test_non_ip_address_is_quoted(self):
        with self.assertLogs("DigiScript.Audit", "INFO") as logs:
            audit("login", "success", remote_ip="1.2.3.4 user_id=0")
        self.assertIn('ip="1.2.3.4 user_id=0"', logs.output[0])

    def test_ipv6_address_is_bare(self):
        with self.assertLogs("DigiScript.Audit", "INFO") as logs:
            audit("login", "success", remote_ip="::1")
        self.assertTrue(logs.records[0].getMessage().endswith(" ip=::1"))


class TestAuthEventsMetric(unittest.TestCase):
    def test_label_names_are_bounded(self):
        self.assertEqual(("event", "result"), auth_events_total._labelnames)

    def test_every_event_result_pair_is_preinitialised(self):
        for event in EVENTS:
            for result in RESULTS:
                self.assertIsNotNone(
                    REGISTRY.get_sample_value(
                        "digiscript_auth_events_total",
                        {"event": event, "result": result},
                    ),
                    f"{event}/{result} missing",
                )

    def test_usernames_do_not_create_series(self):
        before = len(list(auth_events_total.collect()[0].samples))
        with self.assertLogs("DigiScript.Audit", "WARNING"):
            audit("login", "failure", username="user-one")
            audit("login", "failure", username="user-two")
        self.assertEqual(before, len(list(auth_events_total.collect()[0].samples)))
