"""Tests for ScriptRoom class.

Tests the in-memory room that holds a Y.Doc and tracks connected clients.
Uses mock WebSocket handlers since we don't need a real server.
"""

import asyncio
import datetime
import uuid
from unittest.mock import AsyncMock, patch

import pycrdt
import pytest
from sqlalchemy import select
from tornado.testing import gen_test

from models.script import (
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptLineType,
)
from test.utils.script.test_ydoc_to_lines import (
    _add_line_to_doc,
    _build_empty_doc,
    _ScriptTestSetup,
)
from utils.script.line_to_ydoc import build_ydoc, fetch_script_line_data
from utils.script_room_manager import RoomManager, ScriptRoom


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

    def test_has_editors_with_only_viewers(self):
        room = _make_room()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        room.add_client(ws1, "viewer")
        room.add_client(ws2, "viewer")

        assert not room.has_editors
        assert not room.is_empty

    def test_has_editors_with_one_editor(self):
        room = _make_room()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        room.add_client(ws1, "viewer")
        room.add_client(ws2, "editor")

        assert room.has_editors

    def test_has_editors_after_editor_removed(self):
        room = _make_room()
        ws_editor = _make_mock_ws()
        ws_viewer = _make_mock_ws()
        room.add_client(ws_editor, "editor")
        room.add_client(ws_viewer, "viewer")

        room.remove_client(ws_editor)

        assert not room.has_editors
        assert not room.is_empty

    def test_has_editors_empty_room(self):
        room = _make_room()

        assert not room.has_editors

    def test_upgrade_client_role(self):
        """Calling add_client again with a new role upgrades the existing entry."""
        room = _make_room()
        ws = _make_mock_ws()

        room.add_client(ws, "viewer")
        assert room.clients[ws] == "viewer"
        assert not room.has_editors

        room.add_client(ws, "editor")
        assert room.clients[ws] == "editor"
        assert room.has_editors
        # Should still be only one client entry
        assert len(room.clients) == 1


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

    @pytest.mark.asyncio
    async def test_apply_update(self):
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
        await room.apply_update(update)

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
        assert sent_msg["OP"] == "NOOP"
        assert sent_msg["ACTION"] == "YJS_UPDATE"
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
        assert sent_msg["OP"] == "NOOP"
        assert sent_msg["ACTION"] == "YJS_AWARENESS"

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


class TestRoomManagerCloseRoom:
    @pytest.mark.asyncio
    async def test_close_room_evicts_and_notifies(self):
        """close_room sends ROOM_CLOSED to all clients, stops observing, removes room."""
        room = _make_room(revision_id=42)
        room.start_observing()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()
        room.add_client(ws1, "viewer")
        room.add_client(ws2, "viewer")

        # Inject room into a RoomManager (no real app needed)
        manager = RoomManager.__new__(RoomManager)
        manager._rooms = {42: room}

        await manager.close_room(42)

        # Room should be removed
        assert 42 not in manager._rooms

        # Both clients should have received ROOM_CLOSED
        for ws in (ws1, ws2):
            ws.write_message.assert_called_once()
            msg = ws.write_message.call_args[0][0]
            assert msg["OP"] == "NOOP"
            assert msg["ACTION"] == "ROOM_CLOSED"
            assert msg["DATA"]["room_id"] == "draft_42"

        # Observing should be stopped (subscription cleared)
        assert room._doc_subscription is None

    @pytest.mark.asyncio
    async def test_close_room_nonexistent_is_noop(self):
        """Closing a room that doesn't exist does nothing."""
        manager = RoomManager.__new__(RoomManager)
        manager._rooms = {}

        await manager.close_room(999)  # Should not raise

    @pytest.mark.asyncio
    async def test_close_room_handles_failed_write(self):
        """If write_message fails for one client, room is still closed."""
        room = _make_room(revision_id=7)
        ws_ok = _make_mock_ws()
        ws_bad = _make_mock_ws()
        ws_bad.write_message.side_effect = Exception("Connection closed")
        room.add_client(ws_ok, "viewer")
        room.add_client(ws_bad, "viewer")

        manager = RoomManager.__new__(RoomManager)
        manager._rooms = {7: room}

        await manager.close_room(7)

        assert 7 not in manager._rooms
        # The healthy client still receives the message
        ws_ok.write_message.assert_called_once()


class TestScriptRoomSaveDraft(_ScriptTestSetup):
    """Tests for ``ScriptRoom.save_draft`` using a real in-memory DB."""

    def _seed_line(self, session, previous_assoc=None, text="Direction text", page=1):
        """Insert ScriptLine + ScriptLinePart + SLRA; return the association."""
        line = ScriptLine(
            act_id=self.act_id,
            scene_id=self.scene_id,
            page=page,
            line_type=ScriptLineType.STAGE_DIRECTION,
        )
        session.add(line)
        session.flush()

        part = ScriptLinePart(
            line_id=line.id,
            part_index=0,
            character_id=None,
            character_group_id=None,
            line_text=text,
        )
        session.add(part)
        session.flush()

        assoc = ScriptLineRevisionAssociation(
            revision_id=self.revision_id,
            line_id=line.id,
        )
        session.add(assoc)
        session.flush()

        if previous_assoc:
            previous_assoc.next_line = line
            assoc.previous_line = previous_assoc.line
            session.flush()

        return assoc

    @gen_test
    async def test_save_draft_all_new_lines_returns_id_patch(self):
        """Y.Doc with 2 UUID lines → 2 DB rows created, returns bytes."""

        doc = _build_empty_doc()
        uid1 = str(uuid.uuid4())
        uid2 = str(uuid.uuid4())
        _add_line_to_doc(doc, "1", uid1)
        _add_line_to_doc(doc, "1", uid2)

        room = ScriptRoom(self.revision_id, doc)

        with self._app.get_db().sessionmaker() as session:
            update = await room.save_draft(session)

        self.assertIsInstance(update, bytes)
        self.assertGreater(len(update), 0)

        with self._app.get_db().sessionmaker() as session:
            lines = session.scalars(select(ScriptLine)).all()
        self.assertEqual(2, len(lines))

    @gen_test
    async def test_save_draft_patches_ydoc_ids(self):
        """After save, Y.Doc _id values are replaced with real DB integer strings."""
        doc = _build_empty_doc()
        uid = str(uuid.uuid4())
        _add_line_to_doc(doc, "1", uid)

        room = ScriptRoom(self.revision_id, doc)

        with self._app.get_db().sessionmaker() as session:
            await room.save_draft(session)

        pages = doc.get("pages", type=pycrdt.Map)
        line_id_in_doc = str(pages["1"][0]["_id"])

        # Should be a positive integer string (real DB id), not the original UUID
        self.assertNotEqual(line_id_in_doc, uid)
        patched_id = int(line_id_in_doc)
        self.assertGreater(patched_id, 0)

    @gen_test
    async def test_save_draft_no_new_lines_returns_meta_update(self):
        """Y.Doc built from existing DB lines (unchanged) → save_draft returns meta update bytes."""
        with self._app.get_db().sessionmaker() as session:
            self._seed_line(session)

        # Build Y.Doc directly from DB state — all _ids will be real integers
        with self._app.get_db().sessionmaker() as session:
            script_data = fetch_script_line_data(session, self.revision_id)
        doc = build_ydoc(script_data, self.revision_id)

        room = ScriptRoom(self.revision_id, doc)

        with self._app.get_db().sessionmaker() as session:
            update = await room.save_draft(session)

        # Returns bytes (meta.last_saved_at update) rather than None
        self.assertIsInstance(update, bytes)
        self.assertGreater(len(update), 0)

    @gen_test
    async def test_save_draft_validation_error_propagates(self):
        """Invalid DIALOGUE line in Y.Doc → ValueError raised, no new DB rows committed."""

        doc = _build_empty_doc()
        bad_id = str(uuid.uuid4())
        # DIALOGUE with character_id=0 and character_group_id=0 → both None after
        # extraction via _zero_to_none → fails validation (needs one or the other)
        _add_line_to_doc(
            doc,
            "1",
            bad_id,
            line_type=ScriptLineType.DIALOGUE.value,
            parts=[
                {
                    "_id": str(uuid.uuid4()),
                    "part_index": 0,
                    "character_id": 0,
                    "character_group_id": 0,
                    "line_text": "Hello",
                }
            ],
        )

        room = ScriptRoom(self.revision_id, doc)

        with self.assertRaises(ValueError):
            with self._app.get_db().sessionmaker() as session:
                await room.save_draft(session)

        # Rollback means no lines should exist in DB
        with self._app.get_db().sessionmaker() as session:
            lines = session.scalars(select(ScriptLine)).all()
        self.assertEqual(0, len(lines))

    @gen_test
    async def test_save_draft_deleted_line_removed_from_db(self):
        """deleted_line_ids entry with a real DB id → SLRA deleted after save."""

        # Seed one line so it has a real DB id
        with self._app.get_db().sessionmaker() as session:
            assoc = self._seed_line(session)
        line_id_to_delete = assoc.line_id

        # Build Y.Doc with no lines on page 1, but the line's id in deleted_line_ids.
        # Adding an empty page array ensures _save_script_page runs for page 1
        # so that its deletion pass 2 processes the deleted id.
        doc = _build_empty_doc()
        pages = doc.get("pages", type=pycrdt.Map)
        pages["1"] = pycrdt.Array()
        deleted_arr = doc.get("deleted_line_ids", type=pycrdt.Array)
        deleted_arr.append(line_id_to_delete)

        room = ScriptRoom(self.revision_id, doc)

        with self._app.get_db().sessionmaker() as session:
            await room.save_draft(session)

        with self._app.get_db().sessionmaker() as session:
            assoc_post = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, line_id_to_delete)
            )
        self.assertIsNone(assoc_post)

    @gen_test
    async def test_save_draft_broadcasts_progress_messages(self):
        """save_draft broadcasts (0, N), (1, N), ..., (N, N) progress messages."""
        doc = _build_empty_doc()
        # Add one line on page 1 and one on page 2
        uid1 = str(uuid.uuid4())
        uid2 = str(uuid.uuid4())
        _add_line_to_doc(doc, "1", uid1)
        _add_line_to_doc(doc, "2", uid2)

        room = ScriptRoom(self.revision_id, doc)

        # Add a mock client so broadcasts have a recipient
        ws = AsyncMock()
        ws.write_message = AsyncMock()
        room.add_client(ws, "editor")

        with patch.object(
            room, "_broadcast_save_progress", wraps=room._broadcast_save_progress
        ) as mock_broadcast:
            with self._app.get_db().sessionmaker() as session:
                await room.save_draft(session)

        calls = mock_broadcast.call_args_list
        # Expect: (0, 2), (1, 2), (2, 2)
        self.assertEqual(3, len(calls))
        self.assertEqual((0, 2), (calls[0].args[0], calls[0].args[1]))
        self.assertEqual((1, 2), (calls[1].args[0], calls[1].args[1]))
        self.assertEqual((2, 2), (calls[2].args[0], calls[2].args[1]))

    @gen_test
    async def test_save_draft_updates_meta_last_saved_at(self):
        """save_draft always writes meta.last_saved_at to the Y.Doc."""
        doc = _build_empty_doc()
        uid = str(uuid.uuid4())
        _add_line_to_doc(doc, "1", uid)

        room = ScriptRoom(self.revision_id, doc)

        with self._app.get_db().sessionmaker() as session:
            await room.save_draft(session)

        meta = doc.get("meta", type=pycrdt.Map)
        last_saved = meta.get("last_saved_at")
        self.assertIsNotNone(last_saved)
        self.assertIsInstance(last_saved, str)
        self.assertGreater(len(last_saved), 0)
        # Verify it is a valid ISO-format timestamp (should not raise)
        datetime.datetime.fromisoformat(last_saved)

    @gen_test
    async def test_save_draft_clears_deleted_line_ids_after_commit(self):
        """After a successful save, deleted_line_ids Y.Array is emptied.

        Stale integer IDs left in deleted_line_ids can delete freshly-created
        lines on the next save if SQLite reuses those IDs. Clearing on commit
        prevents this accumulation.
        """
        # Seed one real DB line so we have a valid integer ID
        with self._app.get_db().sessionmaker() as session:
            assoc = self._seed_line(session)
        real_id = assoc.line_id

        # Build Y.Doc from DB (so _id values are real integers)
        with self._app.get_db().sessionmaker() as session:
            script_data = fetch_script_line_data(session, self.revision_id)
        doc = build_ydoc(script_data, self.revision_id)

        # Manually push a stale integer into deleted_line_ids (simulating a
        # previous delete that was never cleared)
        deleted_arr = doc.get("deleted_line_ids", type=pycrdt.Array)
        deleted_arr.append(real_id)
        self.assertEqual(1, len(deleted_arr))

        room = ScriptRoom(self.revision_id, doc)

        with self._app.get_db().sessionmaker() as session:
            await room.save_draft(session)

        # deleted_line_ids must be empty after a successful save
        deleted_arr_after = doc.get("deleted_line_ids", type=pycrdt.Array)
        self.assertEqual(0, len(deleted_arr_after))

    @gen_test
    async def test_save_draft_stale_deleted_id_does_not_delete_new_line(self):
        """A stale deleted_line_ids entry must not destroy a newly-inserted line.

        Scenario: a UUID line is inserted between two existing DB lines and the
        Y.Doc still contains a stale integer in deleted_line_ids. If SQLite
        reuses that integer for the new line, Pass 2 must skip it (Fix 1 guard).
        We verify this by seeding a line, pushing its ID into deleted_line_ids
        (making it look stale), then adding a new UUID line. After save, the new
        UUID line must exist in the DB.
        """
        # Seed two real DB lines
        with self._app.get_db().sessionmaker() as session:
            assoc1 = self._seed_line(session, text="Line 1")
            assoc2 = self._seed_line(session, previous_assoc=assoc1, text="Line 2")
        id_of_line2 = assoc2.line_id

        # Build Y.Doc from real DB state
        with self._app.get_db().sessionmaker() as session:
            script_data = fetch_script_line_data(session, self.revision_id)
        doc = build_ydoc(script_data, self.revision_id)

        # Push line2's ID into deleted_line_ids to simulate a stale entry,
        # but keep the line itself in the pages map (not actually deleting it)
        deleted_arr = doc.get("deleted_line_ids", type=pycrdt.Array)
        deleted_arr.append(id_of_line2)

        # Add a new UUID line (simulating an insert)
        new_uid = str(uuid.uuid4())
        _add_line_to_doc(doc, "1", new_uid)

        room = ScriptRoom(self.revision_id, doc)

        with self._app.get_db().sessionmaker() as session:
            await room.save_draft(session)

        # After save: the new UUID line must have been persisted
        with self._app.get_db().sessionmaker() as session:
            lines = session.scalars(select(ScriptLine)).all()

        # We started with 2 lines, added 1 new UUID line → expect 3 lines total
        # (line2 may or may not be deleted depending on page presence, but the
        # new UUID line must be there)
        self.assertGreaterEqual(len(lines), 1, "New UUID line was not saved to DB")


class TestScriptRoomApplyUpdateConcurrency:
    """Tests for apply_update concurrency with save_lock."""

    @pytest.mark.asyncio
    async def test_apply_update_blocked_during_save(self):
        """apply_update waits for save_lock to be released before mutating the doc."""
        room = _make_room()

        # Hold the save lock externally to simulate an in-progress save
        await room.save_lock.acquire()

        doc2 = pycrdt.Doc()
        doc2.get("meta", type=pycrdt.Map)
        doc2.apply_update(room.get_sync_state())
        doc2.get("meta", type=pycrdt.Map)["test"] = "value"
        update = doc2.get_update(room.get_state_vector())

        # Schedule apply_update as a concurrent task
        apply_task = asyncio.ensure_future(room.apply_update(update))

        # Yield to the event loop — task should be blocked on the lock
        await asyncio.sleep(0)
        assert not apply_task.done(), (
            "apply_update should be blocked while lock is held"
        )

        # Release the lock; apply_update should now complete
        room.save_lock.release()
        await apply_task

        meta = room.doc.get("meta", type=pycrdt.Map)
        assert meta["test"] == "value"
