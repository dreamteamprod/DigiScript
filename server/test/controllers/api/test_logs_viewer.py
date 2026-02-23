"""Integration tests for GET /api/v1/logs/view."""

import logging

from tornado import escape

from test.conftest import DigiScriptTestCase
from utils.log_buffer import get_client_buffer, get_server_buffer


def _make_record(msg, level=logging.INFO, name="test", **extra_attrs):
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="fake.py",
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for k, v in extra_attrs.items():
        setattr(record, k, v)
    return record


class TestLogViewerController(DigiScriptTestCase):
    """Tests for the log viewer endpoint."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_and_login_admin(self, username="admin", password="adminpass"):
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": username, "password": password, "is_admin": True}
            ),
        )
        resp = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": username, "password": password}),
        )
        return escape.json_decode(resp.body)["access_token"]

    def _create_and_login_user(self, admin_token, username="user", password="userpass"):
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": username, "password": password, "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        resp = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": username, "password": password}),
        )
        return escape.json_decode(resp.body)["access_token"]

    def _inject_server_entry(self, msg, level=logging.INFO):
        get_server_buffer().emit(_make_record(msg, level=level))

    def _inject_client_entry(self, msg, level=logging.INFO, **extra):
        get_client_buffer().emit(_make_record(msg, level=level, **extra))

    def _fetch_view(self, token=None, **params):
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"/api/v1/logs/view?{qs}" if qs else "/api/v1/logs/view"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.fetch(url, method="GET", headers=headers, raise_error=False)

    # ------------------------------------------------------------------
    # Authentication / authorisation
    # ------------------------------------------------------------------

    def test_unauthenticated_returns_401(self):
        resp = self._fetch_view()
        self.assertEqual(401, resp.code)

    def test_non_admin_returns_401(self):
        admin_token = self._create_and_login_admin()
        user_token = self._create_and_login_user(admin_token)
        resp = self._fetch_view(token=user_token)
        self.assertEqual(401, resp.code)

    def test_admin_returns_200(self):
        token = self._create_and_login_admin()
        resp = self._fetch_view(token=token)
        self.assertEqual(200, resp.code)

    def test_admin_response_structure(self):
        """Response must contain entries, total, returned, source."""
        token = self._create_and_login_admin()
        resp = self._fetch_view(token=token)
        body = escape.json_decode(resp.body)
        for key in ("entries", "total", "returned", "source"):
            self.assertIn(key, body, f"Missing key: {key}")

    # ------------------------------------------------------------------
    # Source selection
    # ------------------------------------------------------------------

    def test_source_defaults_to_server(self):
        token = self._create_and_login_admin()
        resp = self._fetch_view(token=token)
        body = escape.json_decode(resp.body)
        self.assertEqual("server", body["source"])

    def test_source_server_explicit(self):
        token = self._create_and_login_admin()
        resp = self._fetch_view(token=token, source="server")
        body = escape.json_decode(resp.body)
        self.assertEqual("server", body["source"])

    def test_source_client(self):
        token = self._create_and_login_admin()
        resp = self._fetch_view(token=token, source="client")
        body = escape.json_decode(resp.body)
        self.assertEqual("client", body["source"])

    def test_server_and_client_buffers_are_independent(self):
        """Entries injected into server buffer must not appear in client view."""
        self._inject_server_entry("server_only_msg")
        token = self._create_and_login_admin()

        server_resp = escape.json_decode(
            self._fetch_view(token=token, source="server").body
        )
        client_resp = escape.json_decode(
            self._fetch_view(token=token, source="client").body
        )

        server_msgs = [e["message"] for e in server_resp["entries"]]
        client_msgs = [e["message"] for e in client_resp["entries"]]

        self.assertIn("server_only_msg", server_msgs)
        self.assertNotIn("server_only_msg", client_msgs)

    # ------------------------------------------------------------------
    # Level filter
    # ------------------------------------------------------------------

    def test_level_filter_excludes_lower_levels(self):
        """Requesting ERROR+ should hide INFO entries."""
        self._inject_server_entry("info_entry", level=logging.INFO)
        self._inject_server_entry("error_entry", level=logging.ERROR)
        token = self._create_and_login_admin()

        resp = escape.json_decode(
            self._fetch_view(token=token, source="server", level="ERROR").body
        )
        messages = [e["message"] for e in resp["entries"]]
        self.assertIn("error_entry", messages)
        self.assertNotIn("info_entry", messages)

    def test_level_filter_empty_returns_all(self):
        """Empty level param returns entries at all levels."""
        self._inject_server_entry("debug_entry", level=logging.DEBUG)
        self._inject_server_entry("critical_entry", level=logging.CRITICAL)
        token = self._create_and_login_admin()

        resp = escape.json_decode(
            self._fetch_view(token=token, source="server", level="").body
        )
        messages = [e["message"] for e in resp["entries"]]
        self.assertIn("debug_entry", messages)
        self.assertIn("critical_entry", messages)

    def test_warn_alias(self):
        """level=WARN should behave identically to level=WARNING."""
        self._inject_server_entry("warn_entry", level=logging.WARNING)
        self._inject_server_entry("debug_entry_warn_alias", level=logging.DEBUG)
        token = self._create_and_login_admin()

        warn_resp = escape.json_decode(
            self._fetch_view(token=token, source="server", level="WARN").body
        )
        warning_resp = escape.json_decode(
            self._fetch_view(token=token, source="server", level="WARNING").body
        )

        warn_msgs = [e["message"] for e in warn_resp["entries"]]
        warning_msgs = [e["message"] for e in warning_resp["entries"]]

        self.assertIn("warn_entry", warn_msgs)
        self.assertNotIn("debug_entry_warn_alias", warn_msgs)
        self.assertEqual(set(warn_msgs), set(warning_msgs))

    # ------------------------------------------------------------------
    # Search filter
    # ------------------------------------------------------------------

    def test_search_filter(self):
        self._inject_server_entry("unique_search_term_xyz found here")
        self._inject_server_entry("unrelated log entry")
        token = self._create_and_login_admin()

        resp = escape.json_decode(
            self._fetch_view(
                token=token, source="server", search="unique_search_term_xyz"
            ).body
        )
        messages = [e["message"] for e in resp["entries"]]
        self.assertTrue(any("unique_search_term_xyz" in m for m in messages))
        self.assertFalse(any("unrelated log entry" in m for m in messages))

    def test_search_filter_case_insensitive(self):
        self._inject_server_entry("CaseSensitiveTest message")
        token = self._create_and_login_admin()

        resp = escape.json_decode(
            self._fetch_view(
                token=token, source="server", search="casesensitivetest"
            ).body
        )
        messages = [e["message"] for e in resp["entries"]]
        self.assertTrue(any("CaseSensitiveTest" in m for m in messages))

    # ------------------------------------------------------------------
    # Username filter (client source only)
    # ------------------------------------------------------------------

    def test_username_filter_client_source(self):
        self._inject_client_entry("alice log", username="alice")
        self._inject_client_entry("bob log", username="bob")
        token = self._create_and_login_admin()

        resp = escape.json_decode(
            self._fetch_view(token=token, source="client", username="alice").body
        )
        messages = [e["message"] for e in resp["entries"]]
        self.assertIn("alice log", messages)
        self.assertNotIn("bob log", messages)

    def test_username_filter_ignored_for_server_source(self):
        """username param should have no effect on the server source."""
        self._inject_server_entry("server_entry_for_username_test")
        token = self._create_and_login_admin()

        resp_no_filter = escape.json_decode(
            self._fetch_view(token=token, source="server").body
        )
        resp_with_filter = escape.json_decode(
            self._fetch_view(token=token, source="server", username="alice").body
        )
        self.assertEqual(resp_no_filter["total"], resp_with_filter["total"])

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def test_limit(self):
        for i in range(20):
            self._inject_server_entry(f"limit_test_entry {i}")
        token = self._create_and_login_admin()

        resp = escape.json_decode(
            self._fetch_view(token=token, source="server", limit=5).body
        )
        self.assertLessEqual(len(resp["entries"]), 5)
        self.assertEqual(len(resp["entries"]), resp["returned"])

    def test_offset(self):
        """offset should skip entries."""
        # Inject 10 entries that are easy to identify
        for i in range(10):
            self._inject_server_entry(f"offset_test_msg {i}")
        token = self._create_and_login_admin()

        resp_all = escape.json_decode(
            self._fetch_view(
                token=token, source="server", search="offset_test_msg", limit=10
            ).body
        )
        resp_offset = escape.json_decode(
            self._fetch_view(
                token=token,
                source="server",
                search="offset_test_msg",
                limit=10,
                offset=5,
            ).body
        )
        # total should be the same regardless of offset
        self.assertEqual(resp_all["total"], resp_offset["total"])
        # offset result should have 5 fewer entries
        self.assertEqual(resp_all["returned"] - 5, resp_offset["returned"])

    def test_limit_capped_at_1000(self):
        """limit > 1000 should be silently capped, not error."""
        token = self._create_and_login_admin()
        # Just verify a large limit doesn't cause an error
        self.assertEqual(
            200,
            self.fetch(
                "/api/v1/logs/view?limit=9999",
                method="GET",
                headers={"Authorization": f"Bearer {token}"},
                raise_error=False,
            ).code,
        )

    # ------------------------------------------------------------------
    # total vs returned
    # ------------------------------------------------------------------

    def test_total_reflects_filtered_count(self):
        """total should count all matching entries, not just the page."""
        for i in range(15):
            self._inject_server_entry(f"total_test_entry {i}")
        token = self._create_and_login_admin()

        resp = escape.json_decode(
            self._fetch_view(
                token=token, source="server", search="total_test_entry", limit=5
            ).body
        )
        self.assertEqual(15, resp["total"])
        self.assertEqual(5, resp["returned"])

    # ------------------------------------------------------------------
    # SSE stream endpoint — auth and header checks
    # ------------------------------------------------------------------
    # Full streaming content tests require async tooling; these tests verify
    # the auth layer before any streaming begins.

    def _fetch_stream_headers(self, token=None, **params):
        """Perform a GET /api/v1/logs/stream with a very short request timeout.

        The stream never sends a final Content-Length, so self.fetch() would
        hang indefinitely without a timeout.  We use request_timeout=0.5 s;
        the server returns an HTTP 401/403 immediately for auth failures, but
        for a valid admin request the timeout fires after headers are received
        and some initial data may have been sent.
        """
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"/api/v1/logs/stream?{qs}" if qs else "/api/v1/logs/stream"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.fetch(
            url,
            method="GET",
            headers=headers,
            raise_error=False,
            request_timeout=0.5,
        )

    def test_stream_unauthenticated_returns_401(self):
        resp = self._fetch_stream_headers()
        self.assertEqual(401, resp.code)

    def test_stream_non_admin_returns_401(self):
        admin_token = self._create_and_login_admin()
        user_token = self._create_and_login_user(admin_token)
        resp = self._fetch_stream_headers(token=user_token)
        self.assertEqual(401, resp.code)

    def test_stream_backfill_contains_existing_entries(self):
        """Entries injected before connection must appear in the first chunk.

        SSE connections never send a terminal response, so self.fetch() raises
        HTTPTimeoutError when the request_timeout expires.  We use
        streaming_callback to collect chunks as they arrive and inspect the
        accumulated body in the except handler.
        """
        self._inject_server_entry("sse_backfill_unique_xyz")
        token = self._create_and_login_admin()

        received_chunks = []

        try:
            self.fetch(
                "/api/v1/logs/stream?source=server",
                method="GET",
                headers={"Authorization": f"Bearer {token}"},
                raise_error=False,
                request_timeout=1.0,
                streaming_callback=received_chunks.append,
            )
        except Exception:
            # HTTPTimeoutError is expected — the stream stays open indefinitely.
            pass

        self.assertTrue(len(received_chunks) > 0, "No data received from SSE stream")
        full_body = b"".join(received_chunks).decode()
        self.assertIn("sse_backfill_unique_xyz", full_body)
        # Verify SSE wire format: events must begin with "data: "
        data_lines = [ln for ln in full_body.splitlines() if ln.startswith("data: ")]
        self.assertTrue(len(data_lines) > 0)
