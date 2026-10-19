import logging

from tornado import gen
from tornado.httpclient import HTTPRequest
from tornado.httpserver import HTTPServer
from tornado.testing import bind_unused_port, gen_test

from test.conftest import DigiScriptTestCase
from utils.web.size_limits import MIB, install_body_limit_logging


class TestBodyLimitLogging(DigiScriptTestCase):
    @gen_test
    async def test_oversized_body_rejected_and_logged(self):
        """Bodies above the limit are refused and a warning names the limit."""
        limit = MIB
        log_filter = install_body_limit_logging(limit)
        sock, port = bind_unused_port()
        server = HTTPServer(self._app, max_body_size=limit)
        server.add_sockets([sock])
        try:
            request = HTTPRequest(
                f"http://127.0.0.1:{port}/api/v1/auth/login",
                method="POST",
                body="x" * (limit + 1024),
            )
            with self.assertLogs("tornado.general", level="INFO") as logs:
                # The server rejects the request while it is still being sent,
                # so the client sees an error response or a dropped connection.
                try:
                    response = await self.http_client.fetch(request, raise_error=False)
                    self.assertGreaterEqual(response.code, 400)
                except OSError:
                    pass
                await gen.sleep(0.1)
            warnings = [r for r in logs.records if r.levelname == "WARNING"]
            self.assertEqual(1, len(warnings))
            self.assertIn(str(limit), warnings[0].getMessage())
            self.assertIn("127.0.0.1", warnings[0].getMessage())
        finally:
            logging.getLogger("tornado.general").removeFilter(log_filter)
            server.stop()
            sock.close()
