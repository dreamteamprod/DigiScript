"""Tests for the default response headers set by BaseController."""

from test.conftest import DigiScriptTestCase


class TestBaseControllerDefaultHeaders(DigiScriptTestCase):
    def test_security_headers_present(self):
        resp = self.fetch("/api/v1/health", raise_error=False)
        self.assertEqual("nosniff", resp.headers.get("X-Content-Type-Options"))
        self.assertEqual("SAMEORIGIN", resp.headers.get("X-Frame-Options"))
        self.assertEqual("same-origin", resp.headers.get("Referrer-Policy"))

    def test_security_headers_present_on_error_responses(self):
        resp = self.fetch("/api/v1/rbac/user/resources", raise_error=False)
        self.assertEqual(401, resp.code)
        self.assertEqual("nosniff", resp.headers.get("X-Content-Type-Options"))
