"""
Tests for health check endpoint.
"""

import asyncio
import os
import tempfile
import threading
import time
from unittest.mock import patch

from tornado import escape
from tornado.httpclient import HTTPRequest
from tornado.testing import gen_test

from controllers.api.v1 import health
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
    async def test_health_concurrent_polls_share_slow_healthy_probe(self):
        """Overlapping polls during a slow but healthy probe all report ok."""
        calls = []

        def slow(_self):
            calls.append(1)
            time.sleep(0.3)

        with patch.object(HealthController, "_check_database_sync", slow):
            responses = await asyncio.gather(
                *(
                    self.http_client.fetch(
                        self.get_url("/api/v1/health"), raise_error=False
                    )
                    for _ in range(3)
                )
            )

        for response in responses:
            self.assertEqual(200, response.code)
            self.assertEqual(
                "ok", escape.json_decode(response.body)["checks"]["database"]
            )
        self.assertEqual(1, len(calls), "overlapping polls must share one probe")

    @gen_test
    async def test_health_hung_probe_fails_all_callers_without_new_thread(self):
        """A hung probe fails every caller within the timeout; no second probe."""
        release = threading.Event()
        calls = []

        def hang(_self):
            calls.append(1)
            release.wait(5)

        try:
            with (
                patch.object(HealthController, "_check_database_sync", hang),
                patch("controllers.api.v1.health.DB_CHECK_TIMEOUT_SECONDS", 0.1),
            ):
                started = time.monotonic()
                first = await self.http_client.fetch(
                    self.get_url("/api/v1/health"), raise_error=False
                )
                later = await asyncio.gather(
                    *(
                        self.http_client.fetch(
                            self.get_url("/api/v1/health"), raise_error=False
                        )
                        for _ in range(2)
                    )
                )
                elapsed = time.monotonic() - started
        finally:
            release.set()
            if health._probe is not None:
                health._probe.result(timeout=5)

        for response in (first, *later):
            self.assertEqual(503, response.code)
            data = escape.json_decode(response.body)
            self.assertEqual("fail", data["checks"]["database"])
        self.assertLess(elapsed, 2.0)
        self.assertEqual(1, len(calls), "no second probe while one is hung")

        # Once the stuck probe has finished, the endpoint recovers.
        recovered = await self.http_client.fetch(self.get_url("/api/v1/health"))
        self.assertEqual(200, recovered.code)

    @gen_test
    async def test_health_unwritable_storage_returns_503(self):
        """An unwritable storage directory yields 503 without leaking paths."""
        with patch("controllers.api.v1.health._writable", return_value=False):
            response = await self.http_client.fetch(
                self.get_url("/api/v1/health"), raise_error=False
            )

        self.assertEqual(503, response.code)
        data = escape.json_decode(response.body)
        self.assertEqual("degraded", data["status"])
        self.assertEqual("fail", data["checks"]["storage"])
        self.assertEqual("ok", data["checks"]["database"])
        body = response.body.decode()
        for key in (
            "log_path",
            "db_log_path",
            "client_log_path",
            "draft_script_path",
            "compiled_script_path",
        ):
            self.assertNotIn(self._app.digi_settings.get_sync(key), body)

    def test_writable_uses_os_access_on_nearest_ancestor(self):
        """Missing directories are judged by their nearest existing ancestor."""
        with tempfile.TemporaryDirectory() as tmp:
            missing = os.path.join(tmp, "a", "b")
            self.assertTrue(health._writable(missing))
            with patch("controllers.api.v1.health.os.access", return_value=False):
                self.assertFalse(health._writable(missing))

    @gen_test
    async def test_health_missing_storage_setting_is_skipped(self):
        """A storage setting that is not defined (KeyError) is ignored."""
        self.assertIsNone(HealthController._setting(self._app.digi_settings, "nope"))
        real = self._app.digi_settings.get_sync

        def fake(key):
            if key == "draft_script_path":
                raise KeyError(key)
            return real(key)

        with patch.object(self._app.digi_settings, "get_sync", side_effect=fake):
            response = await self.http_client.fetch(self.get_url("/api/v1/health"))
        self.assertEqual(200, response.code)

    @gen_test
    async def test_health_uptime_non_decreasing(self):
        """uptime_seconds is a non-negative, non-decreasing integer."""
        first = escape.json_decode(
            (await self.http_client.fetch(self.get_url("/api/v1/health"))).body
        )
        second = escape.json_decode(
            (await self.http_client.fetch(self.get_url("/api/v1/health"))).body
        )
        self.assertGreaterEqual(first["uptime_seconds"], 0)
        self.assertGreaterEqual(second["uptime_seconds"], first["uptime_seconds"])

    @gen_test
    async def test_health_storage_exception_does_not_leak(self):
        """An unexpected storage-check error is caught and not echoed back."""
        self._app.settings["serve_traceback"] = True
        with patch.object(
            HealthController,
            "_check_storage",
            side_effect=RuntimeError("boom /secret/path"),
        ):
            response = await self.http_client.fetch(
                self.get_url("/api/v1/health"), raise_error=False
            )
        self.assertEqual(503, response.code)
        body = response.body.decode()
        self.assertNotIn("boom", body)
        self.assertNotIn("/secret/path", body)
        self.assertNotIn("Traceback", body)
        self.assertEqual("fail", escape.json_decode(response.body)["checks"]["storage"])

    @gen_test
    async def test_health_unexpected_error_never_serves_traceback(self):
        """Even with serve_traceback on, an escaped error yields minimal JSON."""
        self._app.settings["serve_traceback"] = True
        with patch(
            "controllers.api.v1.health.get_version",
            side_effect=[RuntimeError("boom /secret/path"), "1.2.3"],
        ):
            response = await self.http_client.fetch(
                self.get_url("/api/v1/health"), raise_error=False
            )
        self.assertEqual(503, response.code)
        body = response.body.decode()
        for leaked in ("boom", "/secret/path", "Traceback", "RuntimeError"):
            self.assertNotIn(leaked, body)
        data = escape.json_decode(response.body)
        self.assertEqual("degraded", data["status"])

    @gen_test
    async def test_health_client_errors_keep_default_handling(self):
        """Non-5xx errors (e.g. unsupported method) are not turned into 503."""
        request = HTTPRequest(self.get_url("/api/v1/health"), method="POST", body="{}")
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertLess(response.code, 500)
