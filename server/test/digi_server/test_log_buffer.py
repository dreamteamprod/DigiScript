import logging
import unittest
from datetime import datetime

from utils.log_buffer import (
    LogBufferHandler,
    get_client_buffer,
    get_server_buffer,
)


def _make_record(msg="hello", level=logging.INFO, name="test", **extra_attrs):
    """Helper: create a :class:`logging.LogRecord` with optional extra attrs."""
    record = logging.LogRecord(
        name=name,
        level=level,
        pathname="test_file.py",
        lineno=42,
        msg=msg,
        args=(),
        exc_info=None,
    )
    for key, value in extra_attrs.items():
        setattr(record, key, value)
    return record


class TestLogBufferHandler(unittest.TestCase):
    def setUp(self):
        self.handler = LogBufferHandler(maxlen=100)

    # ------------------------------------------------------------------
    # Basic emit / retrieval
    # ------------------------------------------------------------------

    def test_captures_entry(self):
        """An emitted record should appear in get_entries()."""
        self.handler.emit(_make_record("test message"))
        entries = self.handler.get_entries()
        self.assertEqual(1, len(entries))
        self.assertEqual("test message", entries[0]["message"])

    def test_entry_schema(self):
        """Every required key must be present in an emitted entry."""
        self.handler.emit(
            _make_record("schema check", level=logging.WARNING, name="DigiScript")
        )
        entry = self.handler.get_entries()[0]
        for key in (
            "ts",
            "level",
            "level_no",
            "logger",
            "message",
            "filename",
            "lineno",
        ):
            self.assertIn(key, entry, f"Missing key: {key}")
        self.assertEqual("WARNING", entry["level"])
        self.assertEqual(logging.WARNING, entry["level_no"])
        self.assertEqual("DigiScript", entry["logger"])
        self.assertEqual("schema check", entry["message"])

    def test_empty_buffer_returns_empty_list(self):
        self.assertEqual([], self.handler.get_entries())

    # ------------------------------------------------------------------
    # Circular buffer (maxlen eviction)
    # ------------------------------------------------------------------

    def test_maxlen_eviction(self):
        """When the buffer is full, the oldest entry is dropped."""
        handler = LogBufferHandler(maxlen=5)
        for i in range(6):
            handler.emit(_make_record(f"msg {i}"))
        entries = handler.get_entries()
        self.assertEqual(5, len(entries))
        # Oldest entry (msg 0) must have been evicted
        messages = [e["message"] for e in entries]
        self.assertNotIn("msg 0", messages)
        self.assertIn("msg 5", messages)

    def test_maxlen_not_exceeded(self):
        handler = LogBufferHandler(maxlen=10)
        for i in range(10):
            handler.emit(_make_record(f"msg {i}"))
        self.assertEqual(10, len(handler.get_entries()))

    # ------------------------------------------------------------------
    # Resize
    # ------------------------------------------------------------------

    def test_resize_shrink_keeps_newest(self):
        """Shrinking retains the newest entries."""
        handler = LogBufferHandler(maxlen=100)
        for i in range(100):
            handler.emit(_make_record(f"msg {i}"))
        handler.resize(50)
        entries = handler.get_entries()
        self.assertEqual(50, len(entries))
        # Newest entry must still be present
        self.assertEqual("msg 99", entries[-1]["message"])

    def test_resize_grow_retains_all(self):
        """Growing preserves all existing entries."""
        handler = LogBufferHandler(maxlen=10)
        for i in range(10):
            handler.emit(_make_record(f"msg {i}"))
        handler.resize(200)
        self.assertEqual(10, len(handler.get_entries()))

    def test_resize_same_size(self):
        """Resizing to the current size should be a no-op for content."""
        handler = LogBufferHandler(maxlen=5)
        for i in range(5):
            handler.emit(_make_record(f"msg {i}"))
        handler.resize(5)
        self.assertEqual(5, len(handler.get_entries()))

    # ------------------------------------------------------------------
    # Snapshot isolation
    # ------------------------------------------------------------------

    def test_get_entries_snapshot(self):
        """The returned list is independent of subsequent emits."""
        self.handler.emit(_make_record("first"))
        snapshot = self.handler.get_entries()
        self.handler.emit(_make_record("second"))
        # Snapshot should still only contain the first entry
        self.assertEqual(1, len(snapshot))

    # ------------------------------------------------------------------
    # Client extra fields
    # ------------------------------------------------------------------

    def test_client_extra_fields_present(self):
        """Extra attrs user_id / username / remote_ip are stored in the entry."""
        record = _make_record(
            "client log",
            user_id=7,
            username="alice",
            remote_ip="192.168.1.1",
        )
        self.handler.emit(record)
        entry = self.handler.get_entries()[0]
        self.assertEqual(7, entry["user_id"])
        self.assertEqual("alice", entry["username"])
        self.assertEqual("192.168.1.1", entry["remote_ip"])

    def test_missing_extra_fields_are_none(self):
        """Records without client extra fields should store None, not raise."""
        self.handler.emit(_make_record("plain record"))
        entry = self.handler.get_entries()[0]
        self.assertIsNone(entry["user_id"])
        self.assertIsNone(entry["username"])
        self.assertIsNone(entry["remote_ip"])

    # ------------------------------------------------------------------
    # Singletons
    # ------------------------------------------------------------------

    def test_get_server_buffer_singleton(self):
        """get_server_buffer() returns the same instance on repeated calls."""
        a = get_server_buffer()
        b = get_server_buffer()
        self.assertIs(a, b)

    def test_get_client_buffer_singleton(self):
        """get_client_buffer() returns the same instance on repeated calls."""
        a = get_client_buffer()
        b = get_client_buffer()
        self.assertIs(a, b)

    def test_server_and_client_buffers_are_distinct(self):
        """Server and client buffers must be separate objects."""
        self.assertIsNot(get_server_buffer(), get_client_buffer())

    # ------------------------------------------------------------------
    # Pub/sub (subscribe / unsubscribe)
    # ------------------------------------------------------------------

    def test_subscribe_called_on_emit(self):
        """A registered callback is invoked when a record is emitted."""
        received = []
        self.handler.subscribe(received.append)
        self.handler.emit(_make_record("sub test"))
        self.assertEqual(1, len(received))
        self.assertEqual("sub test", received[0]["message"])

    def test_subscribe_receives_correct_entry(self):
        """The callback receives the same dict that appears in get_entries()."""
        received = []
        self.handler.subscribe(received.append)
        self.handler.emit(_make_record("match test", level=logging.ERROR))
        self.assertEqual(received[0], self.handler.get_entries()[-1])

    def test_unsubscribe_stops_callbacks(self):
        """Calling the returned unsubscribe callable stops future callbacks."""
        received = []
        unsubscribe = self.handler.subscribe(received.append)
        self.handler.emit(_make_record("before"))
        unsubscribe()
        self.handler.emit(_make_record("after"))
        # Only the first emit should have reached the callback.
        self.assertEqual(1, len(received))
        self.assertEqual("before", received[0]["message"])

    def test_multiple_subscribers_all_notified(self):
        """All registered callbacks receive each emitted entry."""
        received_a, received_b = [], []
        self.handler.subscribe(received_a.append)
        self.handler.subscribe(received_b.append)
        self.handler.emit(_make_record("multi"))
        self.assertEqual(1, len(received_a))
        self.assertEqual(1, len(received_b))

    def test_subscriber_exception_does_not_break_emit(self):
        """A callback that raises must not prevent the entry being buffered."""

        def bad_callback(_entry):
            raise RuntimeError("boom")

        self.handler.subscribe(bad_callback)
        # Should not raise — the exception is caught internally.
        self.handler.emit(_make_record("resilient"))
        self.assertEqual(1, len(self.handler.get_entries()))

    # ------------------------------------------------------------------
    # Timestamp format
    # ------------------------------------------------------------------

    def test_timestamp_is_iso8601(self):
        """The ts field should be parseable as an ISO-8601 UTC timestamp."""
        self.handler.emit(_make_record("ts test"))
        ts = self.handler.get_entries()[0]["ts"]
        # Should not raise
        parsed = datetime.fromisoformat(ts)
        self.assertIsNotNone(parsed)
