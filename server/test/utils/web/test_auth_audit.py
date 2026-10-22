import unittest

from prometheus_client import REGISTRY

from utils.web.auth_audit import audit, sanitise


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

    def test_unknown_event_or_result_rejected(self):
        with self.assertRaises(ValueError):
            audit("bogus", "success")
        with self.assertRaises(ValueError):
            audit("login", "maybe")
