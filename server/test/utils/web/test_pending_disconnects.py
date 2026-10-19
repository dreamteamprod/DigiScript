"""Unit tests for the reconnect grace-window timer registry."""

import asyncio

from tornado.testing import gen_test

from test.conftest import DigiScriptTestCase
from utils.web.pending_disconnects import (
    PendingDisconnects,
    disconnect_key,
    room_close_key,
)


class TestPendingDisconnects(DigiScriptTestCase):
    """Timer semantics of :class:`PendingDisconnects`."""

    def setUp(self):
        super().setUp()
        self.registry = PendingDisconnects(grace_seconds=30.0)

    def tearDown(self):
        self.registry.cancel_all()
        super().tearDown()

    @gen_test
    async def test_rescheduling_same_key_fires_once(self):
        """Scheduling a key again replaces the earlier timer; only one fires."""
        calls = []
        key = disconnect_key("u1")
        self.registry.schedule(key, lambda: calls.append("first"), delay=0.01)
        self.registry.schedule(key, lambda: calls.append("second"), delay=0.02)
        await asyncio.sleep(0.1)
        self.assertEqual(["second"], calls)
        self.assertFalse(self.registry.is_scheduled(key))

    @gen_test
    async def test_cancel_unknown_key_returns_false(self):
        self.assertFalse(self.registry.cancel(disconnect_key("nobody")))

    @gen_test
    async def test_cancel_known_key_prevents_firing(self):
        calls = []
        key = disconnect_key("u1")
        self.registry.schedule(key, lambda: calls.append(1), delay=0.01)
        self.assertTrue(self.registry.cancel(key))
        await asyncio.sleep(0.05)
        self.assertEqual([], calls)

    @gen_test
    async def test_negative_delay_is_clamped(self):
        """A negative delay fires on the next loop iteration instead of erroring."""
        calls = []
        self.registry.schedule(disconnect_key("u1"), lambda: calls.append(1), -5)
        await asyncio.sleep(0.02)
        self.assertEqual([1], calls)

    @gen_test
    async def test_default_delay_is_grace_seconds(self):
        self.registry.grace_seconds = 0.01
        calls = []
        self.registry.schedule(disconnect_key("u1"), lambda: calls.append(1))
        await asyncio.sleep(0.05)
        self.assertEqual([1], calls)

    @gen_test
    async def test_raising_callback_leaves_registry_clean(self):
        """A callback that raises still leaves its key unscheduled."""
        key = disconnect_key("u1")

        def _boom():
            raise RuntimeError("boom")

        # Via the IOLoop (Tornado logs the error).
        self.registry.schedule(key, _boom, delay=0)
        await asyncio.sleep(0.02)
        self.assertFalse(self.registry.is_scheduled(key))

        # Via fire(): the error propagates to the caller, registry still clean.
        self.registry.schedule(key, _boom)
        with self.assertRaises(RuntimeError):
            await self.registry.fire(key)
        self.assertFalse(self.registry.is_scheduled(key))

    @gen_test
    async def test_fire_runs_now_and_awaits_coroutines(self):
        calls = []

        async def _cb():
            await asyncio.sleep(0)
            calls.append(1)

        key = room_close_key(7)
        self.registry.schedule(key, _cb)
        self.assertTrue(await self.registry.fire(key))
        self.assertEqual([1], calls)
        self.assertFalse(await self.registry.fire(key))

    @gen_test
    async def test_callback_may_reschedule_its_own_key(self):
        """The key is removed before the callback runs, so a retry can re-arm it."""
        key = disconnect_key("u1")
        self.registry.schedule(key, lambda: self.registry.schedule(key, lambda: None))
        await self.registry.fire(key)
        self.assertTrue(self.registry.is_scheduled(key))

    @gen_test
    async def test_deadline_reports_when_a_timer_fires(self):
        key = disconnect_key("u1")
        self.assertIsNone(self.registry.deadline(key))
        self.registry.schedule(key, lambda: None, delay=10)
        self.assertIsNotNone(self.registry.deadline(key))
        self.registry.cancel(key)
        self.assertIsNone(self.registry.deadline(key))

    @gen_test
    async def test_keys_are_independent_and_cancel_all(self):
        self.registry.schedule(disconnect_key("u1"), lambda: None)
        self.registry.schedule(room_close_key(1), lambda: None)
        self.assertTrue(self.registry.is_pending("u1"))
        self.registry.cancel(disconnect_key("u1"))
        self.assertFalse(self.registry.is_pending("u1"))
        self.assertTrue(self.registry.is_scheduled(room_close_key(1)))
        self.registry.cancel_all()
        self.assertFalse(self.registry.is_scheduled(room_close_key(1)))
