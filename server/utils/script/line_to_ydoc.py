"""Converts ScriptLine models to a pycrdt Y.Doc for collaborative editing.

Two-phase approach for thread safety:
- Phase A (main thread): DB query + extract to plain Python dicts
- Phase B (background thread): CPU-bound Y.Doc construction from plain data

SQLAlchemy Sessions must not cross thread boundaries, so Phase A extracts
all necessary data before Phase B runs in an executor.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pycrdt
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from digi_server.logger import get_logger
from models.script import ScriptLine, ScriptLineRevisionAssociation


if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def fetch_script_line_data(session: Session, revision_id: int) -> list[dict]:
    """Phase A: Query DB and extract script line data as plain dicts.

    Must run on the main thread where the SQLAlchemy session is valid.
    Uses selectinload to eagerly load all associations in a single query
    batch, avoiding N+1 queries.

    :param session: Active SQLAlchemy session.
    :param revision_id: The script revision to extract.
    :returns: List of dicts with line and part data, safe to pass across threads.
    """
    assocs = session.scalars(
        select(ScriptLineRevisionAssociation)
        .where(ScriptLineRevisionAssociation.revision_id == revision_id)
        .options(
            selectinload(ScriptLineRevisionAssociation.line).selectinload(
                ScriptLine.line_parts
            )
        )
    ).all()

    return [
        {
            "line_id": a.line_id,
            "next_line_id": a.next_line_id,
            "previous_line_id": a.previous_line_id,
            "line": {
                "id": a.line.id,
                "act_id": a.line.act_id,
                "scene_id": a.line.scene_id,
                "page": a.line.page,
                "line_type": a.line.line_type.value if a.line.line_type else None,
                "stage_direction_style_id": a.line.stage_direction_style_id,
                "line_parts": sorted(
                    [
                        {
                            "id": p.id,
                            "part_index": p.part_index,
                            "character_id": p.character_id,
                            "character_group_id": p.character_group_id,
                            "line_text": p.line_text or "",
                        }
                        for p in a.line.line_parts
                    ],
                    key=lambda p: p["part_index"] or 0,
                ),
            },
        }
        for a in assocs
    ]


def _build_ydoc_content(script_data: list[dict], revision_id: int) -> pycrdt.Doc:
    """Build a Y.Doc holding the script's lines (no trailing page — see build_ydoc).

    CPU-bound — safe to run in a background thread via run_in_executor.
    No SQLAlchemy Session or ORM objects are used.

    :param script_data: List of dicts from fetch_script_line_data.
    :param revision_id: The revision ID for metadata.
    :returns: A pycrdt.Doc representing the full script.
    """
    doc = pycrdt.Doc()

    # Initialize top-level shared types
    meta = doc.get("meta", type=pycrdt.Map)
    pages = doc.get("pages", type=pycrdt.Map)
    doc.get("deleted_line_ids", type=pycrdt.Array)

    meta["revision_id"] = revision_id
    meta["last_saved_at"] = ""

    # Handle empty script
    if not script_data:
        return doc

    # Build in-memory index for O(1) linked list traversal
    data_by_line_id = {d["line_id"]: d for d in script_data}

    # Find head of linked list (the line with no previous_line_id)
    head = None
    for d in script_data:
        if d["previous_line_id"] is None:
            head = d
            break

    if head is None:
        return doc

    # Walk linked list, grouping lines by page. A composite FK constraint on
    # ScriptLineRevisionAssociation (revision_id, next_line_id) prevents dangling
    # pointers at the DB layer, but a cycle is still structurally possible — the
    # visited-set guard below is defense in depth against both.
    current = head
    current_page = None
    current_page_array = None
    visited: set[int] = set()

    while current is not None:
        if current["line_id"] in visited:
            get_logger().warning(
                f"build_ydoc: cycle detected in linked list for revision "
                f"{revision_id} at line_id={current['line_id']} — stopping traversal"
            )
            break
        visited.add(current["line_id"])

        line_data = current["line"]
        page = line_data["page"]

        # Create new page array if page changed
        page_key = str(page) if page is not None else "0"
        if page_key != current_page:
            current_page = page_key
            current_page_array = pycrdt.Array()
            pages[current_page] = current_page_array

        # Create line Y.Map
        line_map = pycrdt.Map()
        current_page_array.append(line_map)

        line_map["_id"] = str(line_data["id"])
        # Never rewritten: `_id` becomes the DB id when a save patches it, but
        # clients address lines by `_uid` so they survive that patch.
        line_map["_uid"] = str(line_data["id"])
        line_map["act_id"] = (
            line_data["act_id"] if line_data["act_id"] is not None else 0
        )
        line_map["scene_id"] = (
            line_data["scene_id"] if line_data["scene_id"] is not None else 0
        )
        line_map["line_type"] = (
            line_data["line_type"] if line_data["line_type"] is not None else 0
        )
        line_map["stage_direction_style_id"] = (
            line_data["stage_direction_style_id"]
            if line_data["stage_direction_style_id"] is not None
            else 0
        )

        # Create parts Y.Array
        parts_array = pycrdt.Array()
        line_map["parts"] = parts_array

        for part_data in line_data["line_parts"]:
            part_map = pycrdt.Map()
            parts_array.append(part_map)

            part_map["_id"] = str(part_data["id"])
            part_map["_uid"] = str(part_data["id"])
            part_map["part_index"] = (
                part_data["part_index"] if part_data["part_index"] is not None else 0
            )
            part_map["character_id"] = (
                part_data["character_id"]
                if part_data["character_id"] is not None
                else 0
            )
            part_map["character_group_id"] = (
                part_data["character_group_id"]
                if part_data["character_group_id"] is not None
                else 0
            )

            # Y.Text for concurrent text editing
            text = pycrdt.Text(part_data["line_text"])
            part_map["line_text"] = text

        # Advance to next line in linked list
        next_id = current["next_line_id"]
        if next_id is not None and next_id not in data_by_line_id:
            get_logger().warning(
                f"build_ydoc: dangling next_line_id={next_id} for revision "
                f"{revision_id} at line_id={current['line_id']} — "
                f"remaining lines will not appear in the Y.Doc"
            )
        current = data_by_line_id.get(next_id) if next_id is not None else None

    return doc


def numeric_page_keys(pages: pycrdt.Map) -> list[str]:
    """The page keys of a ``pages`` map that are canonical page numbers.

    The one definition of "a page key" shared by the trailing-page check, save and
    the extractor, so a stray key is ignored everywhere rather than tolerated in one
    place and raising in another. Canonical means ``str(int(key)) == key``: that
    excludes ``"01"`` (which ``int()`` reads as page 1 next to a real ``"1"``) and
    keys such as ``"٣"`` (ASCII-only, since ``int()`` accepts non-ASCII digits but
    ``pages[str(n)]`` would then never find them).
    """
    return [
        key
        for key in pages.keys()
        if isinstance(key, str)
        and key.isascii()
        and key.isdecimal()
        and str(int(key)) == key
    ]


def ensure_trailing_page(doc: pycrdt.Doc, repair: bool = False) -> bytes | None:
    """Make sure the doc's last page is an empty one, so clients never create pages.

    ``pages`` is a Y.Map keyed by page number. If two editors each create the same
    new page key, Yjs keeps only one of the two arrays and silently discards the
    other editor's lines. If the array already exists, concurrent inserts into it
    merge cleanly. So the server is the only writer that ever creates a page array:
    it always keeps an empty page at the end, and clients only insert into pages
    that already exist.

    Only the highest numeric page key is inspected, keeping this cheap enough to
    run after every applied update. Non-numeric keys are ignored. Pages are never
    removed, so the doc always *ends* in an empty page; it may also contain earlier
    empty ones.

    :param doc: The Y.Doc to check and, if needed, extend.
    :param repair: If the last page is not a Y.Array (a client update wrote garbage
        under a page key), replace it with an empty page instead of raising, so the
        doc heals and the fix is broadcast. Loading a stored draft leaves this off:
        there a malformed doc is discarded and rebuilt instead.
    :returns: The update that adds the page (to broadcast to clients), or None if the
        doc already ended in an empty page.
    """
    pages = doc.get("pages", type=pycrdt.Map)
    keys = numeric_page_keys(pages)
    last = max((int(key) for key in keys), default=0)
    if keys:
        last_page = pages[str(last)]
        if not isinstance(last_page, pycrdt.Array):
            if not repair:
                raise ValueError(
                    f"Page {last} is not a Y.Array; the draft is malformed"
                )
            state_before = doc.get_state()
            pages[str(last)] = pycrdt.Array()
            return doc.get_update(state_before)
        if len(last_page) == 0:
            return None

    state_before = doc.get_state()
    pages[str(last + 1)] = pycrdt.Array()
    return doc.get_update(state_before)


def backfill_uids(doc: pycrdt.Doc) -> None:
    """Give lines and parts of a draft that predates ``_uid`` a ``_uid`` equal to ``_id``.

    Clients address lines by ``_uid``; without one they fall back to ``_id``, which a
    save rewrites, so such a draft would keep the write-after-save problem.
    """
    pages = doc.get("pages", type=pycrdt.Map)
    for key in numeric_page_keys(pages):
        for line in pages[key]:
            if "_uid" not in line and "_id" in line:
                line["_uid"] = str(line["_id"])
            for part in line.get("parts", []):
                if "_uid" not in part and "_id" in part:
                    part["_uid"] = str(part["_id"])


def build_ydoc(script_data: list[dict], revision_id: int) -> pycrdt.Doc:
    """Phase B: Build a Y.Doc from plain script line data.

    CPU-bound — safe to run in a background thread via run_in_executor.
    No SQLAlchemy Session or ORM objects are used. The doc always ends in an empty
    trailing page (page 1 for an empty script), see ``ensure_trailing_page``.

    :param script_data: List of dicts from fetch_script_line_data.
    :param revision_id: The revision ID for metadata.
    :returns: A pycrdt.Doc representing the full script.
    """
    doc = _build_ydoc_content(script_data, revision_id)
    ensure_trailing_page(doc)
    return doc
