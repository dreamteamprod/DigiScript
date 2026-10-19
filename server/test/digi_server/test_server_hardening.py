import ast
from pathlib import Path

from tornado.httpclient import HTTPRequest
from tornado.httpserver import HTTPServer
from tornado.testing import bind_unused_port, gen_test
from tornado.websocket import WebSocketClosedError, websocket_connect

from digi_server.app_server import MAX_BODY_SIZE, MAX_WEBSOCKET_MESSAGE_SIZE
from test.conftest import DigiScriptTestCase


class TestServerHardening(DigiScriptTestCase):
    def test_debug_option_defaults_to_off(self):
        """Debug mode must be opt-in via ``--debug``."""
        tree = ast.parse(
            (Path(__file__).parents[2] / "main.py").read_text(encoding="utf-8")
        )
        defaults = [
            kw.value.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and getattr(node.func, "id", None) == "define"
            and node.args
            and getattr(node.args[0], "value", None) == "debug"
            for kw in node.keywords
            if kw.arg == "default"
        ]
        self.assertEqual([False], defaults)

    def test_tracebacks_not_served_in_debug_mode(self):
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

    @gen_test
    async def test_oversized_http_body_rejected(self):
        """The production HTTP server refuses bodies above ``MAX_BODY_SIZE``."""
        sock, port = bind_unused_port()
        server = HTTPServer(self._app, max_body_size=MAX_BODY_SIZE)
        server.add_sockets([sock])
        try:
            request = HTTPRequest(
                f"http://127.0.0.1:{port}/api/v1/auth/login",
                method="POST",
                body="x" * (MAX_BODY_SIZE + 1024),
            )
            # The server rejects the request while it is still being sent, so
            # the client sees either an error response or a dropped connection.
            try:
                response = await self.http_client.fetch(request, raise_error=False)
                self.assertGreaterEqual(response.code, 400)
            except OSError:
                pass
        finally:
            server.stop()
            sock.close()

    @gen_test
    async def test_oversized_websocket_message_closes_connection(self):
        """A WebSocket message above the configured cap terminates the socket."""
        limit = self._app.settings["websocket_max_message_size"]
        self.assertEqual(MAX_WEBSOCKET_MESSAGE_SIZE, limit)
        conn = await websocket_connect(
            f"ws://127.0.0.1:{self.get_http_port()}/api/v1/ws"
        )
        try:
            await conn.write_message("x" * (limit + 1024))
        except WebSocketClosedError:
            pass
        # Drain any greeting messages; the server then closes the connection.
        message = await conn.read_message()
        while message is not None:
            message = await conn.read_message()
        self.assertIsNone(message)
