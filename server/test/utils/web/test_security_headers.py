"""Tests for utils/web/security_headers.py."""

import os
import tempfile

from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from utils.web.security_headers import SecureStaticFileHandler


class TestSecureStaticFileHandler(AsyncHTTPTestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        with open(os.path.join(self._dir.name, "page.html"), "w") as f:
            f.write("<p>hi</p>")
        super().setUp()

    def tearDown(self):
        super().tearDown()
        self._dir.cleanup()

    def get_app(self):
        return Application(
            [(r"/docs/(.*)", SecureStaticFileHandler, {"path": self._dir.name})]
        )

    def test_static_file_response_has_security_headers(self):
        resp = self.fetch("/docs/page.html")
        self.assertEqual(200, resp.code)
        self.assertEqual("nosniff", resp.headers.get("X-Content-Type-Options"))
        self.assertEqual("SAMEORIGIN", resp.headers.get("X-Frame-Options"))
        self.assertEqual("same-origin", resp.headers.get("Referrer-Policy"))

    def test_static_not_found_response_has_security_headers(self):
        resp = self.fetch("/docs/missing.html")
        self.assertEqual(404, resp.code)
        self.assertEqual("nosniff", resp.headers.get("X-Content-Type-Options"))
