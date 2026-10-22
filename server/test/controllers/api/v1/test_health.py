"""
Tests for health check endpoint.
"""

import time
from unittest.mock import patch

from tornado import escape
from tornado.testing import gen_test

from controllers.api.v1.health import HealthController
from test.conftest import DigiScriptTestCase


class TestHealthController(DigiScriptTestCase):
    """Test suite for /api/v1/health endpoint."""

    @gen_test
    async def test_health_endpoint_returns_version_and_status(self):
        """Health endpoint should return version and status fields."""
        response = await self.http_client.fetch(self.get_url("/api/v1/health"))

        self.assertEqual(200, response.code)

        data = escape.json_decode(response.body)
        self.assertIn("version", data)
        self.assertIn("status", data)
        self.assertEqual("ok", data["status"])

        # Verify version format (e.g., "0.23.0")
        version = data["version"]
        self.assertIsInstance(version, str)
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

    @gen_test
    async def test_health_endpoint_no_authentication_required(self):
        """Health endpoint should be publicly accessible (no auth required)."""
        # No Authorization header, no X-API-Key header
        response = await self.http_client.fetch(self.get_url("/api/v1/health"))

        # Should succeed without authentication
        self.assertEqual(200, response.code)

    @gen_test
    async def test_health_endpoint_does_not_expose_sensitive_data(self):
        """Health endpoint should NOT expose sensitive configuration."""
        response = await self.http_client.fetch(self.get_url("/api/v1/health"))

        data = escape.json_decode(response.body)

        self.assertEqual(
            {"version", "status", "checks", "uptime_seconds"},
            set(data),
            "Health endpoint should only return the documented fields",
        )

        # Verify sensitive fields are NOT present
        sensitive_fields = [
            "db_path",
            "log_path",
            "db_log_path",
            "debug_mode",
            "current_show",
            "compiled_script_path",
        ]

        for field in sensitive_fields:
            self.assertNotIn(field, data, f"Health endpoint should not expose {field}")

    @gen_test
    async def test_health_endpoint_version_format(self):
        """Health endpoint version should be properly formatted."""
        response = await self.http_client.fetch(self.get_url("/api/v1/health"))

        data = escape.json_decode(response.body)
        version = data["version"]

        # Version should be in semver format (e.g., "0.23.0")
        parts = version.split(".")
        self.assertEqual(
            3, len(parts), "Version should have 3 parts (major.minor.patch)"
        )

        # Each part should be numeric
        for part in parts:
            self.assertTrue(part.isdigit(), f"Version part '{part}' should be numeric")

    @gen_test
    async def test_health_reports_checks_ok(self):
        """Healthy server reports ok for every check."""
        response = await self.http_client.fetch(self.get_url("/api/v1/health"))

        self.assertEqual(200, response.code)
        data = escape.json_decode(response.body)
        self.assertEqual({"database": "ok", "storage": "ok"}, data["checks"])
        self.assertIsInstance(data["uptime_seconds"], int)

    @gen_test
    async def test_health_database_failure_returns_503_without_leaking(self):
        """A failing database yields 503/degraded and no exception text."""
        with patch.object(
            HealthController,
            "_check_database_sync",
            side_effect=RuntimeError("secret-db-detail /var/secret/path"),
        ):
            response = await self.http_client.fetch(
                self.get_url("/api/v1/health"), raise_error=False
            )

        self.assertEqual(503, response.code)
        data = escape.json_decode(response.body)
        self.assertEqual("degraded", data["status"])
        self.assertEqual("fail", data["checks"]["database"])
        self.assertEqual("ok", data["checks"]["storage"])
        self.assertIn("version", data)
        self.assertNotIn("secret-db-detail", response.body.decode())
        self.assertNotIn("/var/secret/path", response.body.decode())

    @gen_test
    async def test_health_database_timeout_returns_503(self):
        """A hung database probe is bounded by the timeout."""

        def hang(_self):
            time.sleep(0.5)

        with (
            patch.object(HealthController, "_check_database_sync", hang),
            patch("controllers.api.v1.health.DB_CHECK_TIMEOUT_SECONDS", 0.05),
        ):
            response = await self.http_client.fetch(
                self.get_url("/api/v1/health"), raise_error=False
            )

        self.assertEqual(503, response.code)
        data = escape.json_decode(response.body)
        self.assertEqual("fail", data["checks"]["database"])

    @gen_test
    async def test_health_unwritable_storage_returns_503(self):
        """An unwritable storage directory yields 503 without leaking paths."""
        with patch("controllers.api.v1.health.os.access", return_value=False):
            response = await self.http_client.fetch(
                self.get_url("/api/v1/health"), raise_error=False
            )

        self.assertEqual(503, response.code)
        data = escape.json_decode(response.body)
        self.assertEqual("degraded", data["status"])
        self.assertEqual("fail", data["checks"]["storage"])
        self.assertEqual("ok", data["checks"]["database"])
        for key in ("log_path", "draft_script_path", "compiled_script_path"):
            path = self._app.digi_settings.get_sync(key)
            self.assertNotIn(path, response.body.decode())
