"""Integration tests for GET /api/v1/admin/db-backups and DELETE /api/v1/admin/db-backups."""

import os
import shutil
import tempfile

from tornado import escape

from test.conftest import DigiScriptTestCase


class TestDbBackupsController(DigiScriptTestCase):
    def setUp(self):
        super().setUp()
        self._tmp_dir = tempfile.mkdtemp()
        self._db_file = os.path.join(self._tmp_dir, "digiscript.sqlite")
        open(self._db_file, "wb").close()
        # Point the db_path setting at our temp file so the controller can find it
        self._app.digi_settings.settings.get("db_path").set_value(
            f"sqlite:///{self._db_file}"
        )

    def tearDown(self):
        shutil.rmtree(self._tmp_dir, ignore_errors=True)
        super().tearDown()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_backup(self, timestamp: int) -> str:
        backup_path = f"{self._db_file}.{timestamp}"
        with open(backup_path, "wb") as f:
            f.write(b"x" * 1024)
        return backup_path

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

    def _fetch_backups(self, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.fetch(
            "/api/v1/admin/db-backups", headers=headers, raise_error=False
        )

    def _delete_backup(self, timestamp, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.fetch(
            f"/api/v1/admin/db-backups?timestamp={timestamp}",
            method="DELETE",
            headers=headers,
            raise_error=False,
        )

    # ------------------------------------------------------------------
    # GET — authentication
    # ------------------------------------------------------------------

    def test_get_unauthenticated_returns_401(self):
        resp = self._fetch_backups()
        self.assertEqual(401, resp.code)

    def test_get_non_admin_returns_401(self):
        admin_token = self._create_and_login_admin()
        user_token = self._create_and_login_user(admin_token)
        resp = self._fetch_backups(token=user_token)
        self.assertEqual(401, resp.code)

    # ------------------------------------------------------------------
    # GET — response shape
    # ------------------------------------------------------------------

    def test_get_admin_no_backups_returns_empty_list(self):
        token = self._create_and_login_admin()
        resp = self._fetch_backups(token=token)
        self.assertEqual(200, resp.code)
        body = escape.json_decode(resp.body)
        self.assertEqual([], body["backups"])
        self.assertEqual(0, body["count"])
        self.assertEqual(0, body["total_size_bytes"])

    def test_get_admin_lists_backup_files(self):
        token = self._create_and_login_admin()
        ts_old = 1700000000
        ts_new = 1700001000
        self._create_backup(ts_old)
        self._create_backup(ts_new)

        resp = self._fetch_backups(token=token)
        self.assertEqual(200, resp.code)
        body = escape.json_decode(resp.body)
        self.assertEqual(2, body["count"])
        self.assertGreater(body["total_size_bytes"], 0)

        timestamps = [b["created_at"] for b in body["backups"]]
        self.assertEqual([ts_new, ts_old], timestamps, "Backups should be newest-first")

    def test_get_backup_metadata_fields(self):
        token = self._create_and_login_admin()
        ts = 1700000000
        self._create_backup(ts)

        resp = self._fetch_backups(token=token)
        body = escape.json_decode(resp.body)
        backup = body["backups"][0]
        self.assertIn("filename", backup)
        self.assertIn("size_bytes", backup)
        self.assertIn("created_at", backup)
        self.assertEqual(ts, backup["created_at"])
        self.assertEqual(1024, backup["size_bytes"])

    def test_get_ignores_non_backup_files(self):
        """Files without a digits-only suffix must not appear in the list."""
        token = self._create_and_login_admin()
        # Create a file that matches the prefix but has a non-digits suffix
        open(f"{self._db_file}.notabackup", "wb").close()
        open(f"{self._db_file}.123abc", "wb").close()

        resp = self._fetch_backups(token=token)
        body = escape.json_decode(resp.body)
        self.assertEqual(0, body["count"])

    # ------------------------------------------------------------------
    # DELETE — authentication
    # ------------------------------------------------------------------

    def test_delete_unauthenticated_returns_401(self):
        resp = self._delete_backup(1700000000)
        self.assertEqual(401, resp.code)

    def test_delete_non_admin_returns_401(self):
        admin_token = self._create_and_login_admin()
        user_token = self._create_and_login_user(admin_token)
        resp = self._delete_backup(1700000000, token=user_token)
        self.assertEqual(401, resp.code)

    # ------------------------------------------------------------------
    # DELETE — validation
    # ------------------------------------------------------------------

    def test_delete_missing_timestamp_returns_400(self):
        token = self._create_and_login_admin()
        resp = self.fetch(
            "/api/v1/admin/db-backups",
            method="DELETE",
            headers={"Authorization": f"Bearer {token}"},
            raise_error=False,
        )
        self.assertEqual(400, resp.code)

    def test_delete_non_digits_timestamp_returns_400(self):
        token = self._create_and_login_admin()
        resp = self._delete_backup("abc123", token=token)
        self.assertEqual(400, resp.code)

    def test_delete_nonexistent_timestamp_returns_404(self):
        token = self._create_and_login_admin()
        resp = self._delete_backup(9999999999, token=token)
        self.assertEqual(404, resp.code)

    # ------------------------------------------------------------------
    # DELETE — success
    # ------------------------------------------------------------------

    def test_delete_valid_backup_removes_file(self):
        token = self._create_and_login_admin()
        ts = 1700000000
        backup_path = self._create_backup(ts)
        self.assertTrue(os.path.isfile(backup_path))

        resp = self._delete_backup(ts, token=token)
        self.assertEqual(200, resp.code)
        self.assertFalse(os.path.isfile(backup_path))

    def test_delete_reduces_count_in_subsequent_get(self):
        token = self._create_and_login_admin()
        ts1 = 1700000000
        ts2 = 1700001000
        self._create_backup(ts1)
        self._create_backup(ts2)

        self._delete_backup(ts1, token=token)

        resp = self._fetch_backups(token=token)
        body = escape.json_decode(resp.body)
        self.assertEqual(1, body["count"])
        self.assertEqual(ts2, body["backups"][0]["created_at"])
