"""Tests for utils/web/json_body.py."""

from unittest.mock import MagicMock

from tornado.web import HTTPError

from test.conftest import DigiScriptTestCase
from utils.web.json_body import get_json_object


def _handler(body: bytes):
    handler = MagicMock()
    handler.request.body = body
    return handler


class TestGetJsonObject(DigiScriptTestCase):
    def test_valid_object_returned(self):
        self.assertEqual({"a": 1}, get_json_object(_handler(b'{"a": 1}')))

    def test_invalid_json_raises_400(self):
        with self.assertRaises(HTTPError) as ctx:
            get_json_object(_handler(b"{not json"))
        self.assertEqual(400, ctx.exception.status_code)

    def test_empty_body_raises_400(self):
        with self.assertRaises(HTTPError) as ctx:
            get_json_object(_handler(b""))
        self.assertEqual(400, ctx.exception.status_code)

    def test_non_object_raises_400(self):
        for body in (b"[1, 2]", b'"text"', b"5", b"null"):
            with self.subTest(body=body), self.assertRaises(HTTPError) as ctx:
                get_json_object(_handler(body))
            self.assertEqual(400, ctx.exception.status_code)
