"""
Tests for health check endpoint.
"""

from tornado import escape
from tornado.testing import gen_test

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

        # Verify ONLY version and status are present
        self.assertEqual(2, len(data), "Health endpoint should return exactly 2 fields")

        # Verify sensitive fields are NOT present
        sensitive_fields = [
            "db_path",
            "log_path",
            "db_log_path",
            "debug_mode",
            "current_show",
            "compiled_script_path",
            "mdns_advertising",
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
