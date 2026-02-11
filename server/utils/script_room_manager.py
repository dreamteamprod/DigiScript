"""Manages collaborative editing rooms for script revisions.

Each ScriptRoom holds a pycrdt Y.Doc and tracks connected WebSocket clients.
The RoomManager handles room lifecycle: creation, persistence, and eviction.
"""

from __future__ import annotations

import asyncio
import base64
import datetime
import glob
import os
import tempfile
import time
from typing import TYPE_CHECKING

import pycrdt
from sqlalchemy import select
from tornado.ioloop import IOLoop

from digi_server.logger import get_logger
from models.script_draft import ScriptDraft
from models.user import User
from utils.script.line_to_ydoc import build_ydoc, fetch_script_line_data


if TYPE_CHECKING:
    from tornado.websocket import WebSocketHandler

    from digi_server.app_server import DigiScriptServer

# How long a room stays alive with no clients before eviction (seconds)
ROOM_IDLE_TIMEOUT = 300  # 5 minutes

# How often to checkpoint the Y.Doc to disk (seconds)
CHECKPOINT_INTERVAL = 30


class ScriptRoom:
    """A collaborative editing room for a single script revision.

    Holds the in-memory Y.Doc and tracks connected WebSocket clients.
    Each client is stored as a tuple of (ws_handler, role) where role
    is 'editor' or 'viewer'.
    """

    def __init__(self, revision_id: int, doc: pycrdt.Doc):
        self.revision_id = revision_id
        self.doc = doc
        self.clients: dict[WebSocketHandler, str] = {}  # ws -> role
        self.save_lock = asyncio.Lock()
        self.last_activity = time.monotonic()
        self._last_checkpoint = time.monotonic()
        self._dirty = False
        self._doc_subscription = None

    def start_observing(self):
        """Start observing doc changes to track dirty state."""
        self._doc_subscription = self.doc.observe(self._on_doc_update)

    def stop_observing(self):
        """Stop observing doc changes."""
        if self._doc_subscription is not None:
            del self._doc_subscription
            self._doc_subscription = None

    def _on_doc_update(self, event):
        """Called when the Y.Doc is modified."""
        self._dirty = True
        self.last_activity = time.monotonic()

    def add_client(self, ws: WebSocketHandler, role: str = "editor"):
        """Add a WebSocket client to this room.

        :param ws: The WebSocket handler.
        :param role: 'editor' or 'viewer'.
        """
        self.clients[ws] = role
        self.last_activity = time.monotonic()
        get_logger().info(
            f"Client joined room for revision {self.revision_id} "
            f"as {role} ({len(self.clients)} total)"
        )

    def remove_client(self, ws: WebSocketHandler):
        """Remove a WebSocket client from this room.

        :param ws: The WebSocket handler to remove.
        """
        self.clients.pop(ws, None)
        get_logger().info(
            f"Client left room for revision {self.revision_id} "
            f"({len(self.clients)} remaining)"
        )

    async def broadcast_update(
        self, update: bytes, sender: WebSocketHandler | None = None
    ):
        """Broadcast a Y.Doc update to all clients except the sender.

        :param update: The binary update to broadcast.
        :param sender: The client that originated the update (excluded from broadcast).
        """
        payload = base64.b64encode(update).decode("ascii")
        message = {
            "OP": "YJS_UPDATE",
            "DATA": {
                "payload": payload,
                "room_id": f"draft_{self.revision_id}",
            },
        }

        for ws in list(self.clients.keys()):
            if ws is sender:
                continue
            try:
                await ws.write_message(message)
            except Exception:
                get_logger().debug(
                    f"Failed to send update to client in room {self.revision_id}"
                )

    async def broadcast_awareness(
        self, data: bytes, sender: WebSocketHandler | None = None
    ):
        """Broadcast awareness state to all clients except the sender.

        :param data: The binary awareness data to broadcast.
        :param sender: The client that originated the update (excluded from broadcast).
        """
        payload = base64.b64encode(data).decode("ascii")
        message = {
            "OP": "YJS_AWARENESS",
            "DATA": {
                "payload": payload,
                "room_id": f"draft_{self.revision_id}",
            },
        }

        for ws in list(self.clients.keys()):
            if ws is sender:
                continue
            try:
                await ws.write_message(message)
            except Exception:
                get_logger().debug(
                    f"Failed to send awareness to client in room {self.revision_id}"
                )

    async def broadcast_members(self, session):
        """Broadcast the current room membership to all clients.

        Sent whenever a client joins or leaves the room so all
        participants have an up-to-date collaborator list.

        :param session: A SQLAlchemy session for looking up usernames.
        """
        members = []
        for ws, role in list(self.clients.items()):
            user_id = getattr(ws, "current_user_id", None)
            username = "Unknown"
            if user_id:
                user = session.get(User, user_id)
                if user:
                    username = user.username or f"User {user_id}"
            members.append({"user_id": user_id, "username": username, "role": role})

        message = {
            "OP": "ROOM_MEMBERS",
            "DATA": {
                "room_id": f"draft_{self.revision_id}",
                "members": members,
            },
        }

        for ws in list(self.clients.keys()):
            try:
                await ws.write_message(message)
            except Exception:
                get_logger().debug(
                    f"Failed to send members to client in room {self.revision_id}"
                )

    def apply_update(self, update: bytes):
        """Apply a binary update to the Y.Doc.

        :param update: The binary update from a client.
        """
        self.doc.apply_update(update)

    def get_sync_state(self) -> bytes:
        """Get the full document state for initial sync.

        :returns: The complete Y.Doc state as bytes.
        """
        return self.doc.get_update()

    def get_state_vector(self) -> bytes:
        """Get the state vector for incremental sync.

        :returns: The state vector as bytes.
        """
        return self.doc.get_state()

    def get_update_for(self, state_vector: bytes) -> bytes:
        """Get a diff update for a client with the given state vector.

        :param state_vector: The client's state vector.
        :returns: The diff update as bytes.
        """
        return self.doc.get_update(state_vector)

    @property
    def is_empty(self) -> bool:
        """Whether the room has no connected clients."""
        return len(self.clients) == 0

    @property
    def needs_checkpoint(self) -> bool:
        """Whether the room needs a checkpoint to disk."""
        return self._dirty and (
            time.monotonic() - self._last_checkpoint > CHECKPOINT_INTERVAL
        )

    def mark_checkpointed(self):
        """Mark the room as having been checkpointed."""
        self._dirty = False
        self._last_checkpoint = time.monotonic()


class RoomManager:
    """Manages ScriptRoom instances and their lifecycle.

    Handles room creation (lazy), persistence (checkpointing to disk),
    and eviction (after idle timeout).
    """

    def __init__(self, application: DigiScriptServer):
        self._application = application
        self._rooms: dict[int, ScriptRoom] = {}  # revision_id -> ScriptRoom
        self._eviction_handle = None

    def start(self):
        """Start the periodic eviction and checkpoint loop."""
        self._schedule_maintenance()

    def stop(self):
        """Stop the maintenance loop and clean up all rooms."""
        if self._eviction_handle is not None:
            IOLoop.current().remove_timeout(self._eviction_handle)
            self._eviction_handle = None

        for room in self._rooms.values():
            room.stop_observing()
        self._rooms.clear()

    def _schedule_maintenance(self):
        """Schedule the next maintenance cycle."""
        self._eviction_handle = IOLoop.current().call_later(
            CHECKPOINT_INTERVAL, self._run_maintenance
        )

    async def _run_maintenance(self):
        """Run periodic maintenance: checkpoint dirty rooms, evict idle ones."""
        try:
            evict_ids = []

            for revision_id, room in list(self._rooms.items()):
                # Checkpoint dirty rooms
                if room.needs_checkpoint:
                    await self._checkpoint_room(room)

                # Mark idle empty rooms for eviction
                if room.is_empty and (
                    time.monotonic() - room.last_activity > ROOM_IDLE_TIMEOUT
                ):
                    evict_ids.append(revision_id)

            # Evict idle rooms
            for revision_id in evict_ids:
                await self._evict_room(revision_id)
        except Exception:
            get_logger().exception("Error during room maintenance")
        finally:
            self._schedule_maintenance()

    async def get_or_create_room(self, revision_id: int) -> ScriptRoom:
        """Get an existing room or create a new one for the given revision.

        If a draft file exists on disk, the Y.Doc is loaded from it.
        Otherwise, the Y.Doc is built from the ScriptLine models.

        :param revision_id: The script revision ID.
        :returns: The ScriptRoom for this revision.
        """
        if revision_id in self._rooms:
            return self._rooms[revision_id]

        doc = await self._load_or_build_doc(revision_id)
        room = ScriptRoom(revision_id, doc)
        room.start_observing()
        self._rooms[revision_id] = room

        get_logger().info(f"Created room for revision {revision_id}")
        return room

    def get_room(self, revision_id: int) -> ScriptRoom | None:
        """Get an existing room without creating one.

        :param revision_id: The script revision ID.
        :returns: The ScriptRoom if it exists, else None.
        """
        return self._rooms.get(revision_id)

    def get_room_for_client(self, ws: WebSocketHandler) -> ScriptRoom | None:
        """Find the room that a WebSocket client belongs to.

        :param ws: The WebSocket handler.
        :returns: The ScriptRoom if found, else None.
        """
        for room in self._rooms.values():
            if ws in room.clients:
                return room
        return None

    async def _load_or_build_doc(self, revision_id: int) -> pycrdt.Doc:
        """Load a Y.Doc from draft file or build from ScriptLine models.

        :param revision_id: The script revision ID.
        :returns: A pycrdt.Doc instance.
        """
        with self._application.get_db().sessionmaker() as session:
            draft: ScriptDraft | None = session.scalar(
                select(ScriptDraft).where(ScriptDraft.revision_id == revision_id)
            )

            if draft and draft.data_path and os.path.exists(draft.data_path):
                # Load from existing draft file
                try:
                    with open(draft.data_path, "rb") as f:
                        data = f.read()
                    doc = pycrdt.Doc()
                    doc.get("meta", type=pycrdt.Map)
                    doc.get("pages", type=pycrdt.Map)
                    doc.get("deleted_line_ids", type=pycrdt.Array)
                    doc.apply_update(data)
                    get_logger().info(
                        f"Loaded draft for revision {revision_id} "
                        f"from {draft.data_path}"
                    )
                    return doc
                except Exception:
                    get_logger().exception(
                        f"Failed to load draft file {draft.data_path}, "
                        f"rebuilding from ScriptLine models"
                    )
                    # Delete stale DB record
                    session.delete(draft)
                    session.commit()
            elif draft and (
                not draft.data_path or not os.path.exists(draft.data_path or "")
            ):
                # Draft record exists but file is missing — clean up
                get_logger().warning(
                    f"Draft record for revision {revision_id} has missing file, "
                    f"removing stale record"
                )
                session.delete(draft)
                session.commit()

            # Build from ScriptLine models
            script_data = fetch_script_line_data(session, revision_id)

        # Phase B: CPU-bound Y.Doc construction in background thread
        doc = await IOLoop.current().run_in_executor(
            None, build_ydoc, script_data, revision_id
        )
        get_logger().info(
            f"Built Y.Doc for revision {revision_id} "
            f"from {len(script_data)} line associations"
        )
        return doc

    async def _checkpoint_room(self, room: ScriptRoom):
        """Checkpoint a room's Y.Doc to disk using atomic write.

        Uses the pattern: write to tmp → fsync → rename for crash safety.

        :param room: The ScriptRoom to checkpoint.
        """
        draft_path = self._get_draft_path(room.revision_id)
        draft_dir = os.path.dirname(draft_path)

        try:
            # Get the full doc state
            state = room.get_sync_state()

            # Atomic write: tmp → fsync → rename
            fd, tmp_path = tempfile.mkstemp(dir=draft_dir, suffix=".yjs.tmp")
            try:
                os.write(fd, state)
                os.fsync(fd)
            finally:
                os.close(fd)
            os.rename(tmp_path, draft_path)

            # Update DB record
            with self._application.get_db().sessionmaker() as session:
                draft: ScriptDraft | None = session.scalar(
                    select(ScriptDraft).where(
                        ScriptDraft.revision_id == room.revision_id
                    )
                )
                now = datetime.datetime.now(tz=datetime.timezone.utc)
                if draft:
                    draft.data_path = draft_path
                    draft.last_modified = now
                else:
                    session.add(
                        ScriptDraft(
                            revision_id=room.revision_id,
                            data_path=draft_path,
                            created_at=now,
                            last_modified=now,
                        )
                    )
                session.commit()

            room.mark_checkpointed()
            get_logger().debug(f"Checkpointed room {room.revision_id} to {draft_path}")
        except Exception:
            get_logger().exception(f"Failed to checkpoint room {room.revision_id}")

    async def _evict_room(self, revision_id: int):
        """Evict an idle room, checkpointing first if dirty.

        :param revision_id: The revision ID of the room to evict.
        """
        room = self._rooms.get(revision_id)
        if room is None:
            return

        # Checkpoint before evicting if there are unsaved changes
        if room._dirty:
            await self._checkpoint_room(room)

        room.stop_observing()
        del self._rooms[revision_id]
        get_logger().info(f"Evicted idle room for revision {revision_id}")

    def _get_draft_path(self, revision_id: int) -> str:
        """Get the filesystem path for a draft file.

        :param revision_id: The script revision ID.
        :returns: The full path to the draft .yjs file.
        """
        draft_dir = self._application.digi_settings.settings.get(
            "draft_script_path"
        ).get_value()
        return os.path.join(draft_dir, f"draft_{revision_id}.yjs")

    async def cleanup_stale_drafts(self):
        """Clean up stale draft files on startup.

        Removes DB records where the file is missing, and removes files
        that have no corresponding DB record.
        """
        draft_dir = self._application.digi_settings.settings.get(
            "draft_script_path"
        ).get_value()

        with self._application.get_db().sessionmaker() as session:
            # Remove DB records with missing files
            removed_drafts = []
            drafts: list[ScriptDraft] = session.scalars(select(ScriptDraft)).all()
            for draft in drafts:
                if not draft.data_path or not os.path.exists(draft.data_path):
                    get_logger().info(
                        f"Removing draft record for revision {draft.revision_id} "
                        f"— data file not found at {draft.data_path}"
                    )
                    session.delete(draft)
                    removed_drafts.append(draft)
            if removed_drafts:
                session.commit()
                get_logger().info(f"Removed {len(removed_drafts)} stale draft records")

            # Remove unreferenced draft files
            if os.path.isdir(draft_dir):
                for yjs_file in glob.glob(os.path.join(draft_dir, "*.yjs")):
                    found = any(
                        d.data_path == yjs_file
                        for d in drafts
                        if d not in removed_drafts
                    )
                    if not found:
                        get_logger().info(
                            f"Removing unreferenced draft file: {yjs_file}"
                        )
                        try:
                            os.remove(yjs_file)
                        except Exception:
                            get_logger().exception(
                                f"Failed to remove draft file: {yjs_file}"
                            )
