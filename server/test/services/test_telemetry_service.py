import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from tornado.httpclient import HTTPClientError
from tornado.testing import gen_test

from models.show import Show, ShowScriptType
from models.user import User
from services.telemetry_service import TelemetryService
from test.conftest import DigiScriptTestCase


class TestTelemetryServiceBuckets(DigiScriptTestCase):
    """Unit tests for TelemetryService's pure bucket-helper logic"""

    def test_bucket_small_boundaries(self):
        self.assertEqual("1", TelemetryService._bucket_small(0))
        self.assertEqual("1", TelemetryService._bucket_small(1))
        self.assertEqual("2-5", TelemetryService._bucket_small(2))
        self.assertEqual("2-5", TelemetryService._bucket_small(5))
        self.assertEqual("6+", TelemetryService._bucket_small(6))
        self.assertEqual("6+", TelemetryService._bucket_small(1000))

    def test_bucket_users_boundaries(self):
        self.assertEqual("1", TelemetryService._bucket_users(0))
        self.assertEqual("1", TelemetryService._bucket_users(1))
        self.assertEqual("2-5", TelemetryService._bucket_users(5))
        self.assertEqual("6-20", TelemetryService._bucket_users(6))
        self.assertEqual("6-20", TelemetryService._bucket_users(20))
        self.assertEqual("21+", TelemetryService._bucket_users(21))


class TestTelemetryServiceState(DigiScriptTestCase):
    """Unit tests for TelemetryService's persisted-state helpers"""

    def setUp(self):
        super().setUp()
        self.service = TelemetryService(application=self._app)

    @gen_test
    async def test_get_or_create_instance_id_persists_and_reuses(self):
        first = await self.service._get_or_create_instance_id()
        second = await self.service._get_or_create_instance_id()

        self.assertEqual(first, second)
        # Must be a valid UUIDv4, matching the collector's validation regex.
        self.assertRegex(
            first,
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        )

    @gen_test
    async def test_get_or_create_first_seen_at_persists_and_reuses(self):
        first = await self.service._get_or_create_first_seen_at()
        second = await self.service._get_or_create_first_seen_at()

        self.assertEqual(first, second)
        # Must round-trip through datetime.fromisoformat, as _build_payload relies on this.
        from datetime import datetime  # noqa: PLC0415

        datetime.fromisoformat(first)


class TestTelemetryServicePayload(DigiScriptTestCase):
    """Unit tests for TelemetryService._build_payload"""

    def setUp(self):
        super().setUp()
        self.service = TelemetryService(application=self._app)

    @gen_test
    async def test_build_payload_shape_on_fresh_install(self):
        payload = await self.service._build_payload()

        # Envelope fields
        for key in (
            "instance_id",
            "app_version",
            "os_platform",
            "os_arch",
            "deployment_method",
            "days_since_install",
            "checkin_count",
            "error_count_recent",
            "metrics",
        ):
            self.assertIn(key, payload)

        self.assertIn(payload["deployment_method"], ("docker", "bare-metal"))
        self.assertEqual(1, payload["checkin_count"])
        self.assertGreaterEqual(payload["days_since_install"], 0)
        self.assertEqual(0, payload["error_count_recent"])

        # Metrics fields, matching the collector's validateDigiscriptMetrics exactly
        metrics = payload["metrics"]
        for key in (
            "shows_bucket",
            "users_bucket",
            "sessions_bucket",
            "rbac_enabled",
            "collab_editing_used",
        ):
            self.assertIn(key, metrics)

        # Fresh install: no shows/users/sessions yet
        self.assertEqual("1", metrics["shows_bucket"])
        self.assertEqual("1", metrics["users_bucket"])
        self.assertEqual("1", metrics["sessions_bucket"])
        self.assertFalse(metrics["rbac_enabled"])

    @gen_test
    async def test_build_payload_reflects_show_and_user_counts(self):
        with self._app.get_db().sessionmaker() as session:
            for i in range(7):
                session.add(Show(name=f"Show {i}", script_mode=ShowScriptType.FULL))
            for i in range(3):
                session.add(User(username=f"user{i}", password="hash"))
            session.commit()

        payload = await self.service._build_payload()

        self.assertEqual("6+", payload["metrics"]["shows_bucket"])
        self.assertEqual("2-5", payload["metrics"]["users_bucket"])

    @gen_test
    async def test_build_payload_increments_checkin_count(self):
        await self._app.digi_settings.set("telemetry_checkin_count", 4)

        payload = await self.service._build_payload()

        self.assertEqual(5, payload["checkin_count"])

    @gen_test
    async def test_error_count_resets_after_being_read(self):
        self.service._error_handler._count = 3

        payload = await self.service._build_payload()
        self.assertEqual(3, payload["error_count_recent"])

        second_payload = await self.service._build_payload()
        self.assertEqual(0, second_payload["error_count_recent"])


class TestTelemetryServiceCheckIn(DigiScriptTestCase):
    """Unit tests for TelemetryService.check_in's HTTP behaviour"""

    def setUp(self):
        super().setUp()
        self.service = TelemetryService(application=self._app)

    @gen_test
    async def test_check_in_success_persists_checkin_count(self):
        with patch.object(
            self.service._http_client, "fetch", AsyncMock(return_value=MagicMock())
        ) as mock_fetch:
            await self.service.check_in()

        mock_fetch.assert_awaited_once()
        request_body = json.loads(mock_fetch.await_args.kwargs["body"])
        self.assertEqual(1, request_body["checkin_count"])

        persisted = await self._app.digi_settings.get("telemetry_checkin_count")
        self.assertEqual(1, persisted)

    @gen_test
    async def test_check_in_never_raises_on_persistent_failure(self):
        with (
            patch.object(
                self.service._http_client,
                "fetch",
                AsyncMock(side_effect=HTTPClientError(500)),
            ),
            patch("services.telemetry_service.asyncio.sleep", AsyncMock()),
        ):
            # Must not raise, even after exhausting all retry attempts.
            await self.service.check_in()

        # A failed check-in must not advance the persisted counter.
        persisted = await self._app.digi_settings.get("telemetry_checkin_count")
        self.assertEqual(0, persisted)

    @gen_test
    async def test_check_in_skips_send_if_payload_build_fails(self):
        with (
            patch.object(
                self.service,
                "_build_payload",
                AsyncMock(side_effect=RuntimeError("boom")),
            ),
            patch.object(self.service._http_client, "fetch", AsyncMock()) as mock_fetch,
        ):
            await self.service.check_in()

        mock_fetch.assert_not_awaited()


class TestTelemetryServiceStartup(DigiScriptTestCase):
    """Unit tests for the DIGISCRIPT_TELEMETRY env var / settings gating in app_server"""

    @gen_test
    async def test_env_var_disables_telemetry_regardless_of_setting(self):
        await self._app.digi_settings.set("telemetry_enabled", True)
        with patch.dict(os.environ, {"DIGISCRIPT_TELEMETRY": "0"}):
            await self._app.start_telemetry_service()

        self.assertIsNone(self._app.telemetry_service)

    @gen_test
    async def test_setting_disabled_prevents_start(self):
        await self._app.digi_settings.set("telemetry_enabled", False)
        await self._app.start_telemetry_service()

        self.assertIsNone(self._app.telemetry_service)

    @gen_test
    async def test_enabled_starts_service(self):
        await self._app.digi_settings.set("telemetry_enabled", True)
        await self._app.start_telemetry_service()

        self.assertIsNotNone(self._app.telemetry_service)

        await self._app.stop_telemetry_service()
        self.assertIsNone(self._app.telemetry_service)
