"""Unit tests for shared WebSocket session-lifecycle helpers."""

from tornado.concurrent import Future
from tornado.testing import gen_test
from tornado.websocket import WebSocketClosedError

from test.conftest import DigiScriptTestCase
from utils.web.ws_session_lifecycle import broadcast, safe_write


class _FakeClient:
    """Stands in for a WebSocket handler.

    With ``closing=True`` it mimics ``WebSocketController.write_message`` on a
    closed socket: it runs ``on_close``, which removes the handler from
    ``application.clients``, while the caller may be iterating that list.
    """

    def __init__(self, app, closing=False, raises=None):
        self.app = app
        self.closing = closing
        self.raises = raises
        self.received = []

    def write_message(self, message):
        if self.raises is not None:
            raise self.raises
        if self.closing:
            self.app.clients.remove(self)
        else:
            self.received.append(message)
        done = Future()
        done.set_result(None)
        return done


class TestBroadcastHelpers(DigiScriptTestCase):
    """A peer that drops out mid-broadcast must not stop others receiving it."""

    def _clients(self, first):
        second = _FakeClient(self._app)
        third = _FakeClient(self._app)
        self._app.clients[:] = [first, second, third]
        return second, third

    def tearDown(self):
        self._app.clients.clear()
        super().tearDown()

    def test_broadcast_survives_peer_removing_itself(self):
        second, third = self._clients(_FakeClient(self._app, closing=True))
        broadcast(self._app, "GET_SCRIPT_CONFIG_STATUS")
        self.assertEqual(1, len(second.received))
        self.assertEqual(1, len(third.received))

    @gen_test
    async def test_ws_send_to_all_survives_peer_removing_itself(self):
        second, third = self._clients(_FakeClient(self._app, closing=True))
        await self._app.ws_send_to_all("NOOP", "GET_SCRIPT_CONFIG_STATUS", {})
        self.assertEqual(1, len(second.received))
        self.assertEqual(1, len(third.received))

    def test_broadcast_survives_peer_raising(self):
        second, third = self._clients(
            _FakeClient(self._app, raises=WebSocketClosedError())
        )
        broadcast(self._app, "NO_LEADER")
        self.assertEqual(1, len(second.received))
        self.assertEqual(1, len(third.received))

    def test_safe_write_swallows_errors(self):
        safe_write(_FakeClient(self._app, raises=WebSocketClosedError()), {})
        safe_write(_FakeClient(self._app, raises=RuntimeError("boom")), {})
