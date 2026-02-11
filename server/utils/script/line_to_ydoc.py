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


def build_ydoc(script_data: list[dict], revision_id: int) -> pycrdt.Doc:
    """Phase B: Build a Y.Doc from plain script line data.

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

    # Walk linked list, grouping lines by page
    current = head
    current_page = None
    current_page_array = None

    while current is not None:
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

        # Create line_parts Y.Array
        parts_array = pycrdt.Array()
        line_map["line_parts"] = parts_array

        for part_data in line_data["line_parts"]:
            part_map = pycrdt.Map()
            parts_array.append(part_map)

            part_map["_id"] = str(part_data["id"])
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
        current = data_by_line_id.get(next_id) if next_id is not None else None

    return doc
