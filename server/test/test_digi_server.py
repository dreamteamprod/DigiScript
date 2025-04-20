import tornado.escape

from .test_utils import DigiScriptTestCase


class TestDigiScriptServer(DigiScriptTestCase):
    def test_debug(self):
        response = self.fetch("/debug")
        response_body = tornado.escape.json_decode(response.body)

        self.assertEqual(200, response.code)
        self.assertTrue("status" in response_body)
        self.assertEqual("OK", response_body["status"])

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
