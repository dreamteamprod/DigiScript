import ast
import asyncio
from pathlib import Path
from unittest.mock import patch

import tornado.escape
from sqlalchemy import func, select
from tornado.testing import gen_test
from tornado.websocket import websocket_connect
from tornado_prometheus import requests_total

from controllers.controllers import ApiDebugController
from models.session import Session
from models.settings import SystemSettings
from models.user import User
from test.conftest import DigiScriptTestCase
from utils.web.request_size_metrics import http_request_body_bytes


class TestDigiScriptServer(DigiScriptTestCase):
    def test_debug(self):
        token = self._create_and_login_admin()
        response = self.fetch("/debug", headers={"Authorization": f"Bearer {token}"})
        response_body = tornado.escape.json_decode(response.body)

        self.assertEqual(200, response.code)
        self.assertTrue("status" in response_body)
        self.assertEqual("OK", response_body["status"])

    def test_debug_requires_admin(self):
        self.assertEqual(401, self.fetch("/debug").code)
        admin = self._create_and_login_admin()
        user = self._create_and_login_user(admin)
        response = self.fetch("/debug", headers={"Authorization": f"Bearer {user}"})
        self.assertEqual(403, response.code)

    def test_debug_mode_is_opt_in(self):
        """Debug mode must be opt-in via ``--debug``."""
        tree = ast.parse(
            (Path(__file__).parents[2] / "main.py").read_text(encoding="utf-8")
        )
        defaults = [
            getattr(kw.value, "value", "<non-literal default>")
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "define"
            and node.args
            and getattr(node.args[0], "value", None) == "debug"
            for kw in node.keywords
            if kw.arg == "default"
        ]
        self.assertEqual(
            [False],
            defaults,
            "--debug must default to the literal False (update this test if the "
            "default is computed)",
        )

    def test_traceback_not_returned_to_client(self):
        """Even with debug=True (as in the test app) no traceback is returned."""
        self.assertTrue(self._app.settings["debug"])
        self.assertFalse(self._app.settings["serve_traceback"])
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body="{not valid json",
        )
        self.assertGreaterEqual(response.code, 400)
        self.assertNotIn(b"Traceback", response.body)
        self.assertNotIn(b".py", response.body)

    def test_request_body_size_observed(self):
        """Request bodies are recorded in the size histogram, labelled by handler."""
        labels = ("ApiFallback", "POST")
        before = self._body_count(*labels)
        self.fetch("/api/v1/nonexistent", method="POST", body="x" * 2000)
        self.assertEqual(before + 1, self._body_count(*labels))

    def test_unknown_http_method_does_not_create_new_series(self):
        """Arbitrary method strings are reported as OTHER, keeping labels bounded."""
        before = self._body_count("ApiFallback", "OTHER")
        for method in ("FOOA1", "FOOB2", "FOOC3"):
            self.fetch(
                "/api/v1/nonexistent",
                method=method,
                body="x" * 10,
                allow_nonstandard_methods=True,
            )
        self.assertEqual(before + 3, self._body_count("ApiFallback", "OTHER"))
        self.assertEqual(0, self._body_count("ApiFallback", "FOOA1"))

    def test_request_without_body_not_observed(self):
        """Body-less requests do not add to the size histogram."""
        before = self._body_count("ApiFallback", "GET")
        self.fetch("/api/v1/nonexistent")
        self.assertEqual(before, self._body_count("ApiFallback", "GET"))

    def test_http_request_metrics_exposed(self):
        """Handled requests produce tornado_http_* samples on /debug/metrics."""
        self.fetch("/api/v1/debug")
        self.fetch("/api/v1/nonexistent")
        body = self.fetch("/debug/metrics").body.decode()
        self.assertRegex(body, r"(?m)^tornado_http_requests_total\{.*\} [1-9]")
        self.assertRegex(
            body,
            r"(?m)^tornado_http_request_duration_seconds_count\{.*\} [1-9]",
        )

    def test_ignored_logging_route_counted_but_not_logged(self):
        """Ignored-logging routes are observed in metrics but emit no access log."""
        before = self._request_count("DebugMetricsController")
        with self.assertNoLogs("tornado.access", level="DEBUG"):
            response = self.fetch("/debug/metrics")
        self.assertEqual(200, response.code)
        self.assertEqual(before + 1, self._request_count("DebugMetricsController"))

    def test_metrics_failure_does_not_break_request(self):
        """A failing metrics observer is swallowed and the request still succeeds."""
        with patch.object(
            self._app, "observe_request", side_effect=RuntimeError("boom")
        ):
            response = self.fetch("/api/v1/debug")
        self.assertEqual(200, response.code)

    def test_metrics_failure_warns_once_and_other_observer_runs(self):
        """Failures are warned about once per interval and observers are independent."""
        before = self._body_count("ApiFallback", "POST")
        with (
            patch.object(self._app, "observe_request", side_effect=RuntimeError("x")),
            self.assertLogs("tornado.access", level="DEBUG") as logs,
        ):
            self.fetch("/api/v1/nonexistent", method="POST", body="x" * 10)
            self.fetch("/api/v1/nonexistent", method="POST", body="x" * 10)
        failures = [r for r in logs.records if "Failed to record" in r.getMessage()]
        self.assertEqual(["WARNING", "DEBUG"], [r.levelname for r in failures])
        self.assertIsNotNone(failures[0].exc_info)
        self.assertEqual(before + 2, self._body_count("ApiFallback", "POST"))

    @gen_test
    async def test_websocket_upgrade_not_counted_as_5xx(self):
        """A 101 upgrade must not land in the 5xx series (tornado_prometheus quirk)."""
        before_5xx = self._status_count("5xx")
        upgrade_logged = asyncio.Event()
        original = self._app.log_request

        def log_request(handler):
            original(handler)
            if handler.get_status() == 101:
                upgrade_logged.set()

        ws_url = self.get_url("/api/v1/ws").replace("http://", "ws://")
        with patch.object(self._app, "log_request", side_effect=log_request):
            ws = await websocket_connect(ws_url)
            ws.close()
            # Wait (bounded) for the server to finish handling the upgrade.
            await asyncio.wait_for(upgrade_logged.wait(), timeout=10)
        self.assertEqual(before_5xx, self._status_count("5xx"))

    def _status_count(self, status):
        total = 0
        for metric in requests_total.collect():
            for sample in metric.samples:
                if sample.name.endswith("_total") and (
                    sample.labels.get("status") == status
                ):
                    total += sample.value
        return total

    def test_access_log_levels(self):
        """2xx logs at DEBUG, 4xx at WARNING and 5xx at ERROR."""
        with self.assertLogs("tornado.access", level="DEBUG") as ok:
            self.fetch("/api/v1/debug")
        self.assertEqual(["DEBUG"], [r.levelname for r in ok.records])
        self.assertIn("200 GET /api/v1/debug", ok.records[0].getMessage())

        with self.assertLogs("tornado.access", level="DEBUG") as warn:
            self.fetch("/api/v1/nonexistent")
        self.assertEqual(["WARNING"], [r.levelname for r in warn.records])

        with (
            patch.object(ApiDebugController, "get", side_effect=RuntimeError("x")),
            self.assertLogs("tornado.access", level="DEBUG") as err,
        ):
            self.fetch("/api/v1/debug")
        self.assertEqual(["ERROR"], [r.levelname for r in err.records])

    def _request_count(self, handler):
        total = 0
        for metric in requests_total.collect():
            for sample in metric.samples:
                if (
                    sample.name.endswith("_total")
                    and sample.labels.get("handler") == handler
                ):
                    total += sample.value
        return total

    @staticmethod
    def _body_count(handler, method):
        for metric in http_request_body_bytes.collect():
            for sample in metric.samples:
                if (
                    sample.name.endswith("_count")
                    and sample.labels.get("handler") == handler
                    and sample.labels.get("method") == method
                ):
                    return sample.value
        return 0

    def test_api_debug(self):
        response = self.fetch("/api/v1/debug")
        response_body = tornado.escape.json_decode(response.body)

        self.assertEqual(200, response.code)
        self.assertTrue("status" in response_body)
        self.assertEqual("OK", response_body["status"])
        self.assertTrue("api_version" in response_body)
        self.assertEqual(1, response_body["api_version"])

    def test_debug_metrics(self):
        response = self.fetch("/debug/metrics")

        self.assertEqual(200, response.code)

    def test_initialization_detects_no_admin(self):
        """Test that initialization correctly detects when no admin exists.

        This tests the query at line 110:
        session.query(User).filter(User.is_admin).first()
        """
        # The server was already initialized in setUp() with no admin
        # Verify it detected the absence correctly
        has_admin = self._app.digi_settings.settings["has_admin_user"].get_value()
        self.assertFalse(has_admin)

    @gen_test
    async def test_validate_has_admin_method(self):
        """Test the _validate_has_admin() method directly.

        This tests the query at line 349:
        session.query(User).filter(User.is_admin).first()
        """
        # Initially no admin
        has_admin = self._app.digi_settings.settings["has_admin_user"].get_value()
        self.assertFalse(has_admin)

        # Create an admin user
        with self._app.get_db().sessionmaker() as session:
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.commit()

        # Call the actual method from app_server.py
        await self._app._validate_has_admin()

        # Verify it detected the admin
        has_admin = self._app.digi_settings.settings["has_admin_user"].get_value()
        self.assertTrue(has_admin)

    def test_initialization_validates_current_show(self):
        """Test that initialization validates current_show setting exists.

        This tests the query at line 119:
        session.query(Show).get(current_show)

        The initialization runs in setUp(). If current_show is invalid,
        it gets reset to default (None).
        """
        # After initialization, current_show should be None (default)
        # because no show exists
        current_show = self._app.digi_settings.settings.get("current_show").get_value()
        self.assertIsNone(current_show)

    def test_initialization_clears_sessions(self):
        """Test that initialization clears all sessions.

        This tests the query at line 150:
        session.query(Session).delete()

        The initialization runs in setUp() and clears the sessions table.
        """
        # After initialization, sessions table should be empty
        with self._app.get_db().sessionmaker() as session:
            count = session.scalar(select(func.count()).select_from(Session))
            self.assertEqual(0, count)

    def test_configure_jwt_creates_secret_if_missing(self):
        """Test that JWT service initialization creates a secret.

        This tests the query at lines 307-309:
        session.query(SystemSettings).filter(SystemSettings.key == "jwt_secret").first()

        The JWT service is configured in __init__, which should create
        a secret if one doesn't exist.
        """
        # The JWT service is already configured in setUp via __init__
        # Verify a secret was created in the database
        with self._app.get_db().sessionmaker() as session:
            jwt_secret = session.scalars(
                select(SystemSettings).where(SystemSettings.key == "jwt_secret")
            ).first()
            self.assertIsNotNone(jwt_secret)
            self.assertIsNotNone(jwt_secret.value)
            self.assertGreater(len(jwt_secret.value), 0)
