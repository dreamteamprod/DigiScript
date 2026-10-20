import json

from tornado.httpclient import HTTPRequest
from tornado.testing import gen_test

from test.conftest import DigiScriptTestCase


class TestRequestBodyLogging(DigiScriptTestCase):
    def _set_redaction(self, value):
        self._app.digi_settings.settings["log_redaction"].set_value(value)

    async def _post_login(self, body):
        request = HTTPRequest(
            self.get_url("/api/v1/auth/login"),
            method="POST",
            body=body,
        )
        with self.assertLogs(level="DEBUG") as captured:
            await self.http_client.fetch(request, raise_error=False)
        return "\n".join(captured.output)

    @gen_test
    async def test_secrets_hidden_when_redaction_enabled(self):
        self._set_redaction(True)
        joined = await self._post_login(
            json.dumps(
                {
                    "username": "nobody",
                    "password": "SENTINEL-PASSWORD",
                    "extra": {"access_token": "SENTINEL-TOKEN"},
                }
            )
        )
        self.assertIn("/api/v1/auth/login", joined)
        self.assertNotIn("SENTINEL-PASSWORD", joined)
        self.assertNotIn("SENTINEL-TOKEN", joined)

    @gen_test
    async def test_body_logged_raw_when_redaction_disabled(self):
        self._set_redaction(False)
        joined = await self._post_login(
            json.dumps({"username": "nobody", "password": "SENTINEL-PASSWORD"})
        )
        self.assertIn("SENTINEL-PASSWORD", joined)

    @gen_test
    async def test_non_json_body_follows_setting(self):
        self._set_redaction(True)
        self.assertNotIn(
            "SENTINEL-RAW", await self._post_login("password=SENTINEL-RAW")
        )
        self._set_redaction(False)
        self.assertIn("SENTINEL-RAW", await self._post_login("password=SENTINEL-RAW"))

    @gen_test
    async def test_decorated_path_absent_from_body_still_logs_redacted(self):
        """A body missing a decorated redaction path (optional old_password) must
        still be logged, with its other secrets redacted, and must not error.
        """
        self._set_redaction(True)
        request = HTTPRequest(
            self.get_url("/api/v1/auth/change-password"),
            method="PATCH",
            body=json.dumps({"new_password": "SENTINEL-NEW"}),
        )
        with self.assertLogs(level="DEBUG") as captured:
            await self.http_client.fetch(request, raise_error=False)
        joined = "\n".join(captured.output)
        self.assertIn("/api/v1/auth/change-password", joined)
        self.assertNotIn("SENTINEL-NEW", joined)
        self.assertNotIn("Uncaught exception", joined)

    @gen_test
    async def test_json_string_body_does_not_break_logging(self):
        """A body that decodes to a bare JSON string is still logged and does not
        raise in on_finish (the handler's own rejection of it is separate).
        """
        self._set_redaction(True)
        joined = await self._post_login('"{"')
        self.assertIn("DEBUG:DigiScript:POST /api/v1/auth/login", joined)
        self.assertNotIn("on_finish", joined)

    @gen_test
    async def test_confirm_password_redacted_without_decorator(self):
        self._set_redaction(True)
        joined = await self._post_login(
            json.dumps({"username": "x", "confirmPassword": "SENTINEL-CONFIRM"})
        )
        self.assertNotIn("SENTINEL-CONFIRM", joined)
