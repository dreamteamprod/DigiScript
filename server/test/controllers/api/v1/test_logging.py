import json

from tornado import escape
from tornado.testing import gen_test

from test.conftest import DigiScriptTestCase


class TestLoggingController(DigiScriptTestCase):
    @gen_test
    async def test_logging_endpoint_success(self):
        """Test that the logging endpoint successfully receives logs."""
        payload = {
            "level": "INFO",
            "message": "Test message from client",
            "extra": {"source": "unit-test"},
        }
        response = await self.http_client.fetch(
            self.get_url("/api/v1/logs"),
            method="POST",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(200, response.code)
        data = escape.json_decode(response.body)
        self.assertEqual("OK", data["status"])

    @gen_test
    async def test_logging_endpoint_disabled(self):
        """Test that the logging endpoint returns 403 when disabled in settings."""
        # Disable client logging in settings
        await self._app.digi_settings.set("client_log_enabled", False)

        payload = {"level": "INFO", "message": "Test message from client"}
        response = await self.http_client.fetch(
            self.get_url("/api/v1/logs"),
            method="POST",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            raise_error=False,
        )
        self.assertEqual(403, response.code)
        data = escape.json_decode(response.body)
        self.assertEqual("Client logging is disabled", data["message"])

        # Re-enable for other tests
        await self._app.digi_settings.set("client_log_enabled", True)

    @gen_test
    async def test_logging_endpoint_invalid_json(self):
        """Test that the logging endpoint returns 400 for invalid JSON."""
        response = await self.http_client.fetch(
            self.get_url("/api/v1/logs"),
            method="POST",
            body="invalid json",
            headers={"Content-Type": "application/json"},
            raise_error=False,
        )
        self.assertEqual(400, response.code)

    @gen_test
    async def test_logging_endpoint_different_levels(self):
        """Test that the logging endpoint accepts various log levels."""
        for level in ["DEBUG", "INFO", "WARN", "ERROR"]:
            payload = {"level": level, "message": f"Test level {level}"}
            response = await self.http_client.fetch(
                self.get_url("/api/v1/logs"),
                method="POST",
                body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            self.assertEqual(200, response.code)
