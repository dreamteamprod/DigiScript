import json
import unittest

from tornado.httpclient import HTTPRequest
from tornado.testing import gen_test

from test.conftest import DigiScriptTestCase
from utils.web.log_redaction import REDACTED, redact_sensitive_keys


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


class TestRestBodyLogging(DigiScriptTestCase):
    @gen_test
    async def test_sentinel_secrets_never_logged(self):
        body = {
            "username": "nobody",
            "password": "SENTINEL-PASSWORD",
            "extra": {"access_token": "SENTINEL-TOKEN"},
        }
        request = HTTPRequest(
            self.get_url("/api/v1/auth/login"),
            method="POST",
            body=json.dumps(body),
        )
        with self.assertLogs(level="DEBUG") as captured:
            await self.http_client.fetch(request, raise_error=False)
        joined = "\n".join(captured.output)
        self.assertIn("/api/v1/auth/login", joined)
        self.assertNotIn("SENTINEL-PASSWORD", joined)
        self.assertNotIn("SENTINEL-TOKEN", joined)

    @gen_test
    async def test_non_json_body_not_logged(self):
        request = HTTPRequest(
            self.get_url("/api/v1/auth/login"),
            method="POST",
            body="password=SENTINEL-RAW",
        )
        with self.assertLogs(level="DEBUG") as captured:
            await self.http_client.fetch(request, raise_error=False)
        self.assertNotIn("SENTINEL-RAW", "\n".join(captured.output))

    def test_default_log_level_is_info(self):
        self.assertEqual("INFO", self._app.digi_settings.settings["log_level"].default)
