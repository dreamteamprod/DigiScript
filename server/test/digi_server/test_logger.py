import asyncio
import gc
import logging
import sys
import threading
import unittest
import warnings

from tornado.ioloop import IOLoop

from digi_server.logger import (
    ALL_LOGGERS,
    CLIENT_LEVEL_MAP,
    UNHANDLED_ERRORS,
    install_exception_hooks,
    logger,
    map_client_level,
    uninstall_exception_hooks,
)


class TestMapClientLevel(unittest.TestCase):
    def test_trace_maps_to_level_5(self):
        self.assertEqual(5, map_client_level("TRACE"))

    def test_debug_maps_to_logging_debug(self):
        self.assertEqual(logging.DEBUG, map_client_level("DEBUG"))

    def test_info_maps_to_logging_info(self):
        self.assertEqual(logging.INFO, map_client_level("INFO"))

    def test_warn_maps_to_logging_warning(self):
        """loglevel npm uses WARN; Python uses WARNING (30)."""
        self.assertEqual(logging.WARNING, map_client_level("WARN"))

    def test_error_maps_to_logging_error(self):
        self.assertEqual(logging.ERROR, map_client_level("ERROR"))

    def test_silent_maps_above_critical(self):
        """SILENT has no Python equivalent; should suppress all output."""
        self.assertEqual(logging.CRITICAL + 1, map_client_level("SILENT"))

    def test_unknown_level_falls_back_to_info(self):
        self.assertEqual(logging.INFO, map_client_level("UNKNOWN"))
        self.assertEqual(logging.INFO, map_client_level(""))
        self.assertEqual(logging.INFO, map_client_level("NOTSET"))

    def test_case_insensitive(self):
        self.assertEqual(logging.WARNING, map_client_level("warn"))
        self.assertEqual(logging.INFO, map_client_level("info"))
        self.assertEqual(5, map_client_level("trace"))

    def test_client_level_map_contains_all_expected_keys(self):
        expected = {"TRACE", "DEBUG", "INFO", "WARN", "ERROR", "SILENT"}
        self.assertEqual(expected, set(CLIENT_LEVEL_MAP.keys()))


class _ListHandler(logging.Handler):
    def __init__(self):
        super().__init__(logging.DEBUG)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class TestExceptionHooks(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._excepthook = sys.excepthook
        self._thread_hook = threading.excepthook
        self._warnings_captured = logging._warnings_showwarning is not None
        self._levels = {lg.name: lg.level for lg in ALL_LOGGERS}
        self.handler = _ListHandler()
        for lg in ALL_LOGGERS:
            lg.addHandler(self.handler)
        logger.setLevel(logging.DEBUG)
        uninstall_exception_hooks()

    def tearDown(self):
        uninstall_exception_hooks()
        sys.excepthook = self._excepthook
        threading.excepthook = self._thread_hook
        logging.captureWarnings(self._warnings_captured)
        for lg in ALL_LOGGERS:
            lg.removeHandler(self.handler)
            lg.setLevel(self._levels[lg.name])

    @staticmethod
    def _count(source):
        return UNHANDLED_ERRORS.labels(source=source)._value.get()

    def test_all_loggers_cover_stdlib_sources(self):
        names = {lg.name for lg in ALL_LOGGERS}
        self.assertTrue({"asyncio", "alembic", "py.warnings", "DigiScript"} <= names)
        self.assertNotIn("sqlalchemy.engine", names)
        self.assertNotIn("root", names)

    def test_install_is_idempotent_and_restores_originals(self):
        install_exception_hooks()
        first = sys.excepthook
        install_exception_hooks()
        self.assertIs(first, sys.excepthook)
        self.assertIsNot(self._excepthook, sys.excepthook)
        uninstall_exception_hooks()
        self.assertIs(self._excepthook, sys.excepthook)
        self.assertIs(self._thread_hook, threading.excepthook)

    def test_sys_excepthook_logs_critical_and_counts(self):
        install_exception_hooks()
        before = self._count("sys_excepthook")
        try:
            raise ValueError("boom-sys")
        except ValueError:
            sys.excepthook(*sys.exc_info())
        self.assertEqual(before + 1, self._count("sys_excepthook"))
        records = [r for r in self.handler.records if r.name == "DigiScript"]
        self.assertEqual(1, len(records))
        self.assertEqual(logging.CRITICAL, records[0].levelno)
        self.assertIn("boom-sys", repr(records[0].exc_info[1]))

    def test_sys_excepthook_keeps_default_for_keyboard_interrupt(self):
        calls = []
        sys.excepthook = lambda *a: calls.append(a)
        install_exception_hooks()
        before = self._count("sys_excepthook")
        sys.excepthook(KeyboardInterrupt, KeyboardInterrupt(), None)
        self.assertEqual(1, len(calls))
        self.assertEqual(before, self._count("sys_excepthook"))
        self.assertEqual([], self.handler.records)

    def test_thread_excepthook_logs_and_counts(self):
        install_exception_hooks()
        before = self._count("thread")

        def target():
            raise RuntimeError("boom-thread")

        t = threading.Thread(target=target, name="obs-test-thread")
        t.start()
        t.join()
        self.assertEqual(before + 1, self._count("thread"))
        records = [r for r in self.handler.records if r.name == "DigiScript"]
        self.assertEqual(1, len(records))
        self.assertEqual(logging.ERROR, records[0].levelno)
        self.assertIn("obs-test-thread", records[0].getMessage())
        self.assertIn("boom-thread", repr(records[0].exc_info[1]))

    async def test_loop_callback_exception_logged_with_traceback(self):
        loop = asyncio.get_running_loop()
        install_exception_hooks(loop)
        before = self._count("asyncio")
        done = asyncio.Event()

        def bad_callback():
            loop.call_soon(done.set)
            raise RuntimeError("boom-callback")

        # Raw asyncio callbacks (call_soon/call_later) reach the loop handler.
        # IOLoop.add_callback catches exceptions itself and logs them to
        # tornado.application, which is already attached to the same handlers.
        loop.call_soon(bad_callback)
        await asyncio.wait_for(done.wait(), 5)
        await asyncio.sleep(0.05)
        self.assertEqual(before + 1, self._count("asyncio"))
        records = [
            r for r in self.handler.records if "boom-callback" in repr(r.exc_info)
        ]
        # Exactly one record carries the traceback (tornado's own logger may
        # also report the callback; filter to ours and the asyncio logger).
        ours = [r for r in records if r.name == "DigiScript"]
        self.assertEqual(1, len(ours))
        self.assertEqual(logging.ERROR, ours[0].levelno)
        self.assertIsNotNone(ours[0].exc_info[2])
        self.assertEqual([], [r for r in records if r.name == "asyncio"])

    async def test_ioloop_add_callback_exception_logged_once(self):
        loop = asyncio.get_running_loop()
        install_exception_hooks(loop)
        before = self._count("asyncio")
        done = asyncio.Event()

        def bad_callback():
            loop.call_soon(done.set)
            raise RuntimeError("boom-add-callback")

        IOLoop.current().add_callback(bad_callback)
        await asyncio.wait_for(done.wait(), 5)
        await asyncio.sleep(0.05)
        records = [
            r for r in self.handler.records if "boom-add-callback" in repr(r.exc_info)
        ]
        self.assertEqual(1, len(records))
        self.assertEqual("tornado.application", records[0].name)
        self.assertEqual(before, self._count("asyncio"))

    async def test_unretrieved_task_exception_logged_once(self):
        loop = asyncio.get_running_loop()
        install_exception_hooks(loop)
        before = self._count("asyncio")

        async def bad():
            raise RuntimeError("boom-task")

        task = asyncio.create_task(bad())
        await asyncio.sleep(0.05)
        del task
        gc.collect()
        await asyncio.sleep(0.05)
        self.assertEqual(before + 1, self._count("asyncio"))
        records = [r for r in self.handler.records if "boom-task" in repr(r.exc_info)]
        self.assertEqual(1, len(records))
        self.assertIn("Task exception was never retrieved", records[0].getMessage())
        self.assertIn("future: <Task", records[0].getMessage())

    def test_warnings_reach_py_warnings_logger_once(self):
        install_exception_hooks()
        with warnings.catch_warnings():
            warnings.simplefilter("always")
            logging.captureWarnings(True)
            warnings.warn("obs-test-warning", UserWarning)
        records = [r for r in self.handler.records if r.name == "py.warnings"]
        self.assertEqual(1, len(records))
        self.assertIn("obs-test-warning", records[0].getMessage())
