import json

from tornado import escape

from controllers.api.v1.logging import (
    MAX_BATCH_ENTRIES,
    MAX_MESSAGE_LENGTH,
    ClientLogRateLimiter,
)
from digi_server.logger import get_logger
from test.conftest import DigiScriptTestCase


class TestLoggingController(DigiScriptTestCase):
    def _post(self, path, payload, token=None, body=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.fetch(
            path,
            method="POST",
            body=body if body is not None else json.dumps(payload),
            headers=headers,
        )

    def test_logging_endpoint_success(self):
        token = self._create_and_login_admin()
        payload = {
            "level": "INFO",
            "message": "Test message from client",
            "extra": {"source": "unit-test"},
        }
        response = self._post("/api/v1/logs", payload, token)
        self.assertEqual(200, response.code)
        self.assertEqual("OK", escape.json_decode(response.body)["status"])

    def test_logging_requires_authentication(self):
        payload = {"level": "INFO", "message": "anonymous"}
        with self.assertNoLogs(get_logger("Client"), level="DEBUG"):
            self.assertEqual(401, self._post("/api/v1/logs", payload).code)
            self.assertEqual(
                401, self._post("/api/v1/logs/batch", {"batch": [payload]}).code
            )

    def test_logging_endpoint_disabled(self):
        token = self._create_and_login_admin()
        self.io_loop.run_sync(
            lambda: self._app.digi_settings.set("client_log_enabled", False)
        )
        response = self._post("/api/v1/logs", {"level": "INFO", "message": "x"}, token)
        self.assertEqual(403, response.code)
        self.assertEqual(
            "Client logging is disabled", escape.json_decode(response.body)["message"]
        )

    def test_logging_endpoint_invalid_json(self):
        token = self._create_and_login_admin()
        response = self._post("/api/v1/logs", None, token, body="invalid json")
        self.assertEqual(400, response.code)

    def test_logging_endpoint_different_levels(self):
        token = self._create_and_login_admin()
        for level in ["DEBUG", "INFO", "WARN", "ERROR"]:
            response = self._post(
                "/api/v1/logs", {"level": level, "message": f"lvl {level}"}, token
            )
            self.assertEqual(200, response.code)

    def test_batch_over_limit_rejected(self):
        token = self._create_and_login_admin()
        batch = [{"level": "INFO", "message": "m"}] * (MAX_BATCH_ENTRIES + 1)
        self.assertEqual(
            413, self._post("/api/v1/logs/batch", {"batch": batch}, token).code
        )
        batch = batch[:MAX_BATCH_ENTRIES]
        self.assertEqual(
            200, self._post("/api/v1/logs/batch", {"batch": batch}, token).code
        )

    def test_message_truncated_and_newlines_escaped(self):
        token = self._create_and_login_admin()
        message = "A\nFAKE LOG LINE " + "x" * (MAX_MESSAGE_LENGTH * 2)
        with self.assertLogs(get_logger("Client"), level="DEBUG") as logs:
            response = self._post(
                "/api/v1/logs", {"level": "INFO", "message": message}, token
            )
        self.assertEqual(200, response.code)
        out = logs.records[0].getMessage()
        self.assertNotIn("\n", out)
        self.assertIn("[truncated]", out)
        self.assertLess(len(out), MAX_MESSAGE_LENGTH + 1500)

    def test_oversized_extra_replaced(self):
        token = self._create_and_login_admin()
        with self.assertLogs(get_logger("Client"), level="DEBUG") as logs:
            self._post(
                "/api/v1/logs",
                {"level": "INFO", "message": "m", "extra": {"k": "y" * 100000}},
                token,
            )
        out = logs.records[0].getMessage()
        self.assertIn("too large", out)
        self.assertNotIn("yyyyyyyyyy", out)

    def test_non_string_fields_coerced(self):
        token = self._create_and_login_admin()
        batch = [
            {"level": 5, "message": {"a": 1}, "extra": "not-a-dict"},
            {"level": None, "message": None, "extra": [1, 2]},
            "not-an-object",
        ]
        response = self._post("/api/v1/logs/batch", {"batch": batch}, token)
        self.assertEqual(200, response.code)

    def test_rate_limit_returns_429(self):
        token = self._create_and_login_admin()
        self._app.client_log_limiter = ClientLogRateLimiter(limit=3, window=60)
        payload = {"level": "INFO", "message": "m"}
        for _ in range(3):
            self.assertEqual(200, self._post("/api/v1/logs", payload, token).code)
        response = self._post("/api/v1/logs", payload, token)
        self.assertEqual(429, response.code)
        self.assertIn("Retry-After", response.headers)

    def test_rate_limiter_window_resets_and_prunes(self):
        limiter = ClientLogRateLimiter(limit=2, window=10)
        self.assertEqual(0, limiter.check("a", 2, now=0))
        self.assertGreater(limiter.check("a", 1, now=1), 0)
        self.assertEqual(0, limiter.check("b", 1, now=11))
        self.assertNotIn("a", limiter._windows)
