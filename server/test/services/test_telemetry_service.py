import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select
from tornado.httpclient import HTTPClientError
from tornado.testing import gen_test

from models.cue import CueType
from models.settings import SystemSettings
from models.show import Show, ShowScriptType
from models.user import User
from rbac.role import Role
from services.telemetry_service import TelemetryService
from test.conftest import DigiScriptTestCase


def _get_system_setting(app, key: str):
    with app.get_db().sessionmaker() as session:
        row = session.scalars(
            select(SystemSettings).where(SystemSettings.key == key)
        ).first()
        return row.value if row else None


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

    def test_get_or_create_instance_id_persists_and_reuses(self):
        with self._app.get_db().sessionmaker() as session:
            first = self.service._get_or_create_instance_id(session)
            second = self.service._get_or_create_instance_id(session)

        self.assertEqual(first, second)
        # Must be a valid UUIDv4, matching the collector's validation regex.
        self.assertRegex(
            first,
            r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
        )
        # Persisted in the DB-backed SystemSettings table, not the file-based settings.
        self.assertEqual(first, _get_system_setting(self._app, "telemetry_instance_id"))

    def test_get_or_create_first_seen_at_persists_and_reuses(self):
        with self._app.get_db().sessionmaker() as session:
            first = self.service._get_or_create_first_seen_at(session)
            second = self.service._get_or_create_first_seen_at(session)

        self.assertEqual(first, second)
        # Must round-trip through datetime.fromisoformat, as _build_payload relies on this.
        from datetime import datetime  # noqa: PLC0415

        datetime.fromisoformat(first)


class TestTelemetryServicePayload(DigiScriptTestCase):
    """Unit tests for TelemetryService._build_payload"""

    def setUp(self):
        super().setUp()
        self.service = TelemetryService(application=self._app)

    def test_build_payload_shape_on_fresh_install(self):
        payload = self.service._build_payload()

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

    def test_build_payload_reflects_show_and_user_counts(self):
        with self._app.get_db().sessionmaker() as session:
            for i in range(7):
                session.add(Show(name=f"Show {i}", script_mode=ShowScriptType.FULL))
            for i in range(3):
                session.add(User(username=f"user{i}", password="hash"))
            session.commit()

        payload = self.service._build_payload()

        self.assertEqual("6+", payload["metrics"]["shows_bucket"])
        self.assertEqual("2-5", payload["metrics"]["users_bucket"])

    def test_build_payload_increments_checkin_count(self):
        with self._app.get_db().sessionmaker() as session:
            session.add(SystemSettings(key="telemetry_checkin_count", value="4"))
            session.commit()

        payload = self.service._build_payload()

        self.assertEqual(5, payload["checkin_count"])

    def test_error_count_resets_after_being_read(self):
        self.service._error_handler._count = 3

        payload = self.service._build_payload()
        self.assertEqual(3, payload["error_count_recent"])

        second_payload = self.service._build_payload()
        self.assertEqual(0, second_payload["error_count_recent"])

    def test_rbac_enabled_false_for_single_user_auto_grant(self):
        """A lone creator's auto-granted role (e.g. from creating a cue type) must not
        read as "RBAC enabled" — that would make the metric true for nearly every install."""
        with self._app.get_db().sessionmaker() as session:
            user = User(username="solo-admin", password="hash")
            session.add(user)
            session.commit()
            cue_type = CueType(prefix="LX", description="Lighting", colour="#ffffff")
            session.add(cue_type)
            session.commit()
            self._app.rbac.give_role(user, cue_type, Role.READ | Role.WRITE)

        payload = self.service._build_payload()
        self.assertFalse(payload["metrics"]["rbac_enabled"])

    def test_rbac_enabled_true_for_multiple_distinct_users(self):
        with self._app.get_db().sessionmaker() as session:
            user_a = User(username="user-a", password="hash")
            user_b = User(username="user-b", password="hash")
            session.add_all([user_a, user_b])
            session.commit()
            cue_type = CueType(prefix="SND", description="Sound", colour="#000000")
            session.add(cue_type)
            session.commit()
            self._app.rbac.give_role(user_a, cue_type, Role.READ)
            self._app.rbac.give_role(user_b, cue_type, Role.READ)

        payload = self.service._build_payload()
        self.assertTrue(payload["metrics"]["rbac_enabled"])

    def test_rbac_enabled_false_when_all_roles_revoked(self):
        """revoke_role() clears the permission bitmask but doesn't delete the row — a
        revoked grant must not count as "holds a role", even with multiple such rows."""
        with self._app.get_db().sessionmaker() as session:
            user_a = User(username="user-a", password="hash")
            user_b = User(username="user-b", password="hash")
            session.add_all([user_a, user_b])
            session.commit()
            cue_type = CueType(prefix="SND", description="Sound", colour="#000000")
            session.add(cue_type)
            session.commit()
            self._app.rbac.give_role(user_a, cue_type, Role.READ)
            self._app.rbac.give_role(user_b, cue_type, Role.READ)
            self._app.rbac.revoke_role(user_a, cue_type, Role.READ)
            self._app.rbac.revoke_role(user_b, cue_type, Role.READ)

        payload = self.service._build_payload()
        self.assertFalse(payload["metrics"]["rbac_enabled"])


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

        persisted = _get_system_setting(self._app, "telemetry_checkin_count")
        self.assertEqual("1", persisted)

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

        # A failed check-in must not create/advance the persisted counter row at all.
        persisted = _get_system_setting(self._app, "telemetry_checkin_count")
        self.assertIsNone(persisted)

    @gen_test
    async def test_check_in_skips_send_if_payload_build_fails(self):
        with (
            patch.object(
                self.service,
                "_build_payload",
                MagicMock(side_effect=RuntimeError("boom")),
            ),
            patch.object(self.service._http_client, "fetch", AsyncMock()) as mock_fetch,
        ):
            await self.service.check_in()

        mock_fetch.assert_not_awaited()

    @gen_test
    async def test_check_in_does_not_retry_a_local_persistence_failure(self):
        """A failure writing checkin_count after a successful POST is a local problem, not
        a network one — it must not be treated as a failed send and retried."""
        with (
            patch.object(
                self.service._http_client, "fetch", AsyncMock(return_value=MagicMock())
            ) as mock_fetch,
            patch.object(
                self.service,
                "_set_checkin_count",
                MagicMock(side_effect=RuntimeError("db is locked")),
            ),
        ):
            # Must not raise, and must not retry the already-successful POST.
            await self.service.check_in()

        mock_fetch.assert_awaited_once()


class TestTelemetryServiceLifecycle(DigiScriptTestCase):
    """Unit tests for TelemetryService.start/stop's scheduling and guard behaviour"""

    def setUp(self):
        super().setUp()
        self.service = TelemetryService(application=self._app)

    def tearDown(self):
        self.service.stop()
        super().tearDown()

    def test_start_is_idempotent(self):
        self.service.start()
        first_handle = self.service._startup_timeout_handle

        self.service.start()

        # A second start() must not schedule a second, independent startup chain.
        self.assertIs(first_handle, self.service._startup_timeout_handle)

    def test_stop_cancels_pending_startup_chain(self):
        self.service.start()
        self.assertIsNotNone(self.service._startup_timeout_handle)

        self.service.stop()

        self.assertIsNone(self.service._startup_timeout_handle)

    @gen_test
    async def test_stop_during_jitter_window_prevents_first_check_in(self):
        with patch.object(self.service, "check_in", AsyncMock()) as mock_check_in:
            self.service.start()
            self.service.stop()

            # Drive the scheduled callback manually, simulating the jitter timer firing
            # after stop() — this is the exact race the fix guards against.
            self.service._schedule_first_check_in()
            await self.service._first_check_in()

        mock_check_in.assert_not_awaited()
        self.assertIsNone(self.service._periodic_callback)

    def test_http_client_uses_force_instance(self):
        """Must not share VersionChecker's cached AsyncHTTPClient instance — stop() closes
        this client, which would otherwise break VersionChecker's client too."""
        from utils.version_checker import VersionChecker  # noqa: PLC0415

        version_checker_client = VersionChecker(application=self._app)._http_client
        self.assertIsNot(self.service._http_client, version_checker_client)


class TestTelemetryServiceStartup(DigiScriptTestCase):
    """Unit tests for the DIGISCRIPT_TELEMETRY env var / settings gating in app_server"""

    @gen_test
    async def test_env_var_disables_telemetry_regardless_of_setting(self):
        await self._app.digi_settings.set("telemetry_enabled", True)
        with patch.dict(os.environ, {"DIGISCRIPT_TELEMETRY": "0"}):
            await self._app.start_telemetry_service()

        self.assertIsNone(self._app.telemetry_service)

    @gen_test
    async def test_env_var_broadened_spellings_also_disable(self):
        for value in ("off", "disabled", "n", "FALSE"):
            self._app.telemetry_service = None
            await self._app.digi_settings.set("telemetry_enabled", True)
            with patch.dict(os.environ, {"DIGISCRIPT_TELEMETRY": value}):
                await self._app.start_telemetry_service()

            self.assertIsNone(self._app.telemetry_service, f"value={value!r}")

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

    @gen_test
    async def test_start_telemetry_service_is_safe_to_call_twice(self):
        """Covers the "started twice" scenario toggle_telemetry's dispatch-via-IOLoop could
        otherwise produce under a rapid enable/disable/enable sequence."""
        await self._app.digi_settings.set("telemetry_enabled", True)
        await self._app.start_telemetry_service()
        first_service = self._app.telemetry_service

        await self._app.start_telemetry_service()

        self.assertIs(first_service, self._app.telemetry_service)
        await self._app.stop_telemetry_service()

    @gen_test
    async def test_toggle_telemetry_sync_wrapper_dispatches_via_ioloop(self):
        """toggle_telemetry() itself is a sync callback (it's a SettingsObject callback_fn,
        called synchronously) that must correctly hand off to the async _toggle_telemetry."""
        import asyncio  # noqa: PLC0415

        await self._app.digi_settings.set("telemetry_enabled", False)
        self._app.telemetry_service = None

        await self._app.digi_settings.set("telemetry_enabled", True)
        self._app.toggle_telemetry()

        # toggle_telemetry() only schedules _toggle_telemetry via IOLoop.add_callback; give
        # it a real tick to actually run before asserting on its effect.
        await asyncio.sleep(0.05)

        self.assertIsNotNone(self._app.telemetry_service)
        await self._app.stop_telemetry_service()
