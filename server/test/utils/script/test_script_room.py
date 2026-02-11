"""Tests for ScriptRoom class.

Tests the in-memory room that holds a Y.Doc and tracks connected clients.
Uses mock WebSocket handlers since we don't need a real server.
"""

from unittest.mock import AsyncMock

import pycrdt
import pytest

from utils.script_room_manager import ScriptRoom


def _make_mock_ws():
    """Create a mock WebSocket handler."""
    ws = AsyncMock()
    ws.write_message = AsyncMock()
    return ws


def _make_room(revision_id=1):
    """Create a ScriptRoom with a simple Y.Doc."""
    doc = pycrdt.Doc()
    doc.get("meta", type=pycrdt.Map)
    doc.get("pages", type=pycrdt.Map)
    doc.get("deleted_line_ids", type=pycrdt.Array)
    return ScriptRoom(revision_id, doc)


class TestScriptRoomClients:
    def test_add_client(self):
        room = _make_room()
        ws = _make_mock_ws()

        room.add_client(ws, "editor")

        assert ws in room.clients
        assert room.clients[ws] == "editor"
        assert not room.is_empty

    def test_add_viewer_client(self):
        room = _make_room()
        ws = _make_mock_ws()

        room.add_client(ws, "viewer")

        assert room.clients[ws] == "viewer"

    def test_remove_client(self):
        room = _make_room()
        ws = _make_mock_ws()
        room.add_client(ws, "editor")

        room.remove_client(ws)

        assert ws not in room.clients
        assert room.is_empty

    def test_remove_nonexistent_client_is_noop(self):
        room = _make_room()
        ws = _make_mock_ws()

        room.remove_client(ws)  # Should not raise

        assert room.is_empty


class TestScriptRoomSync:
    def test_get_sync_state_returns_bytes(self):
        room = _make_room()
        state = room.get_sync_state()
        assert isinstance(state, bytes)
        assert len(state) > 0

    def test_get_state_vector_returns_bytes(self):
        room = _make_room()
        sv = room.get_state_vector()
        assert isinstance(sv, bytes)

    def test_apply_update(self):
        room = _make_room()
        meta = room.doc.get("meta", type=pycrdt.Map)
        meta["revision_id"] = 42

        # Create a second doc, apply state, modify, get update
        doc2 = pycrdt.Doc()
        doc2.get("meta", type=pycrdt.Map)
        doc2.apply_update(room.get_sync_state())
        doc2.get("meta", type=pycrdt.Map)["revision_id"] = 99

        # Get the diff and apply
        update = doc2.get_update(room.get_state_vector())
        room.apply_update(update)

        assert meta["revision_id"] == 99

    def test_get_update_for_state_vector(self):
        room = _make_room()
        room.doc.get("meta", type=pycrdt.Map)

        # Empty state vector should return full state
        empty_sv = pycrdt.Doc().get_state()
        diff = room.get_update_for(empty_sv)
        assert isinstance(diff, bytes)
        assert len(diff) > 0


class TestScriptRoomBroadcast:
    @pytest.mark.asyncio
    async def test_broadcast_update_excludes_sender(self):
        room = _make_room()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        ws3 = _make_mock_ws()
        room.add_client(ws1, "editor")
        room.add_client(ws2, "editor")
        room.add_client(ws3, "viewer")

        update = b"test_update_data"
        await room.broadcast_update(update, sender=ws1)

        ws1.write_message.assert_not_called()
        assert ws2.write_message.call_count == 1
        assert ws3.write_message.call_count == 1

        # Verify message format
        sent_msg = ws2.write_message.call_args[0][0]
        assert sent_msg["OP"] == "YJS_UPDATE"
        assert "payload" in sent_msg["DATA"]
        assert "room_id" in sent_msg["DATA"]

    @pytest.mark.asyncio
    async def test_broadcast_awareness_excludes_sender(self):
        room = _make_room()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        room.add_client(ws1, "editor")
        room.add_client(ws2, "editor")

        await room.broadcast_awareness(b"awareness_data", sender=ws1)

        ws1.write_message.assert_not_called()
        assert ws2.write_message.call_count == 1

        sent_msg = ws2.write_message.call_args[0][0]
        assert sent_msg["OP"] == "YJS_AWARENESS"

    @pytest.mark.asyncio
    async def test_broadcast_handles_failed_write(self):
        """If write_message fails for one client, others still receive."""
        room = _make_room()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        ws3 = _make_mock_ws()
        ws2.write_message.side_effect = Exception("Connection closed")
        room.add_client(ws1, "editor")
        room.add_client(ws2, "editor")
        room.add_client(ws3, "editor")

        # Should not raise
        await room.broadcast_update(b"data", sender=ws1)

        # ws3 should still receive even though ws2 failed
        assert ws3.write_message.call_count == 1


class TestScriptRoomDirtyTracking:
    def test_room_starts_clean(self):
        room = _make_room()
        assert not room._dirty
        assert not room.needs_checkpoint

    def test_doc_update_marks_dirty(self):
        room = _make_room()
        room.start_observing()

        meta = room.doc.get("meta", type=pycrdt.Map)
        meta["test"] = "value"

        assert room._dirty

    def test_mark_checkpointed_clears_dirty(self):
        room = _make_room()
        room._dirty = True

        room.mark_checkpointed()

        assert not room._dirty
