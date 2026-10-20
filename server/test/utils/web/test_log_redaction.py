import unittest

from jsonpath import JSONPatch

from utils.web.log_redaction import (
    REDACTED,
    apply_path_redactions,
    redact_sensitive_keys,
)


class TestRedactSensitiveKeys(unittest.TestCase):
    def test_redacts_nested_and_case_insensitive(self):
        data = {
            "username": "bob",
            "Password": "p1",
            "nested": {"new_password": "p2", "list": [{"api_token": "t"}, 3]},
            "token": "abc",
        }
        result = redact_sensitive_keys(data)
        self.assertEqual("bob", result["username"])
        self.assertEqual(REDACTED, result["Password"])
        self.assertEqual(REDACTED, result["nested"]["new_password"])
        self.assertEqual(REDACTED, result["nested"]["list"][0]["api_token"])
        self.assertEqual(3, result["nested"]["list"][1])
        self.assertEqual(REDACTED, result["token"])

    def test_does_not_mutate_input(self):
        data = {"password": "p"}
        redact_sensitive_keys(data)
        self.assertEqual({"password": "p"}, data)

    def test_scalars_pass_through(self):
        self.assertEqual("x", redact_sensitive_keys("x"))
        self.assertIsNone(redact_sensitive_keys(None))


class TestApplyPathRedactions(unittest.TestCase):
    def _patch(self, *paths):
        patch = JSONPatch()
        for path in paths:
            patch.replace(path, REDACTED)
        return patch

    def test_missing_path_does_not_stop_later_paths(self):
        body = {"new_password": "secret"}
        apply_path_redactions(self._patch("/old_password", "/new_password"), body)
        self.assertEqual({"new_password": REDACTED}, body)

    def test_non_container_body_is_ignored(self):
        for body in ("{", 5, None):
            apply_path_redactions(self._patch("/password"), body)
