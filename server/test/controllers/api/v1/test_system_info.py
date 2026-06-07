"""Integration tests for GET /api/v1/system/info."""

from tornado import escape

from test.conftest import DigiScriptTestCase


class TestSystemInfoController(DigiScriptTestCase):
    def _fetch_system_info(self, token=None):
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return self.fetch("/api/v1/system/info", headers=headers, raise_error=False)

    def test_unauthenticated_returns_401(self):
        resp = self._fetch_system_info()
        self.assertEqual(401, resp.code)

    def test_non_admin_returns_401(self):
        admin_token = self._create_and_login_admin()
        user_token = self._create_and_login_user(admin_token)
        resp = self._fetch_system_info(token=user_token)
        self.assertEqual(401, resp.code)

    def test_authenticated_returns_200_with_expected_keys(self):
        token = self._create_and_login_admin()
        resp = self._fetch_system_info(token=token)
        self.assertEqual(200, resp.code)
        body = escape.json_decode(resp.body)
        self.assertIn("hostname", body)
        self.assertIn("ip_address", body)
        self.assertIn("port", body)

    def test_hostname_is_non_empty_string(self):
        token = self._create_and_login_admin()
        resp = self._fetch_system_info(token=token)
        body = escape.json_decode(resp.body)
        self.assertIsInstance(body["hostname"], str)
        self.assertGreater(len(body["hostname"]), 0)

    def test_ip_address_is_non_empty_string(self):
        token = self._create_and_login_admin()
        resp = self._fetch_system_info(token=token)
        body = escape.json_decode(resp.body)
        self.assertIsInstance(body["ip_address"], str)
        self.assertGreater(len(body["ip_address"]), 0)

    def test_port_is_integer(self):
        token = self._create_and_login_admin()
        resp = self._fetch_system_info(token=token)
        body = escape.json_decode(resp.body)
        self.assertIsInstance(body["port"], int)
