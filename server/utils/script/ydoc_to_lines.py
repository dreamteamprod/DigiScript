"""Convert a pycrdt Y.Doc back to database ScriptLine records.

Entry points
------------
- ``extract_lines_from_ydoc`` — read Y.Doc into plain Python data (fast, sync)
- ``_save_script_page`` — persist one page of Y.Doc data to the DB (called by
  ``ScriptRoom.save_draft``)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pycrdt
from sqlalchemy import select

from digi_server.logger import get_logger
from models.cue import CueAssociation
from models.script import (
    ScriptCuts,
    ScriptLine,
    ScriptLineRevisionAssociation,
)
from utils.script.line_helpers import create_new_line, validate_line


if TYPE_CHECKING:
    from models.script import ScriptRevision
    from models.show import Show
    from utils.database import DigiDBSession


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _zero_to_none(value):
    """Convert 0 to None for nullable FK fields.

    The Y.Doc uses ``0`` as a sentinel for ``None`` because CRDT maps cannot
    store ``None`` values.
    """
    return None if value == 0 else value


def _parse_db_id(line_id) -> int | None:
    """Return integer DB id, or None if *line_id* is a UUID / new-line sentinel.

    :param line_id: The raw ``_id`` value from a Y.Map (may be a UUID string,
        an integer string, an integer, or 0).
    :returns: The positive integer id if this is an existing DB row, else None.
    """
    try:
        v = int(float(str(line_id)))
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None  # UUID string → new line


# ---------------------------------------------------------------------------
# Extract
# ---------------------------------------------------------------------------


def extract_lines_from_ydoc(
    doc: pycrdt.Doc,
) -> tuple[list[dict], list[int]]:
    """Read the Y.Doc and return plain Python data.

    MUST run synchronously in the event loop (not in an executor) to ensure a
    consistent point-in-time snapshot.

    :param doc: The pycrdt Y.Doc to extract from.
    :returns: ``(lines_by_page, deleted_line_ids)`` where ``lines_by_page`` is
        a list of ``{"page": int, "lines": list[dict]}`` dicts ordered by page
        number, and ``deleted_line_ids`` is a list of integer DB ids of lines
        that were deleted by editors.
    """
    pages_map = doc.get("pages", type=pycrdt.Map)
    deleted_arr = doc.get("deleted_line_ids", type=pycrdt.Array)

    # Collect deleted line IDs — skip UUIDs (lines never saved to DB)
    deleted_line_ids: list[int] = []
    for i in range(len(deleted_arr)):
        raw = deleted_arr[i]
        db_id = _parse_db_id(raw)
        if db_id is not None:
            deleted_line_ids.append(db_id)
        else:
            get_logger().debug(
                f"extract_lines_from_ydoc: skipping non-DB deleted_line_id {raw!r}"
            )

    get_logger().debug(f"extract_lines_from_ydoc: deleted_line_ids={deleted_line_ids}")

    # Extract pages sorted by page number
    lines_by_page: list[dict] = []
    page_keys = sorted(pages_map.keys(), key=int)

    get_logger().debug(
        f"extract_lines_from_ydoc: {len(page_keys)} page(s): {page_keys}"
    )

    for page_key in page_keys:
        page_num = int(page_key)
        page_array = pages_map[page_key]
        lines: list[dict] = []

        get_logger().debug(
            f"extract_lines_from_ydoc: page {page_num} has {len(page_array)} line(s)"
        )

        for i in range(len(page_array)):
            line_map = page_array[i]
            line_parts: list[dict] = []

            parts_array = line_map["parts"]
            for j in range(len(parts_array)):
                part_map = parts_array[j]
                line_parts.append(
                    {
                        "_id": part_map["_id"],
                        "part_index": part_map["part_index"],
                        "character_id": _zero_to_none(part_map["character_id"]),
                        "character_group_id": _zero_to_none(
                            part_map["character_group_id"]
                        ),
                        "line_text": str(part_map["line_text"]),
                    }
                )

            raw_id = line_map["_id"]
            lines.append(
                {
                    "_id": raw_id,
                    "act_id": _zero_to_none(line_map["act_id"]),
                    "scene_id": _zero_to_none(line_map["scene_id"]),
                    "line_type": _zero_to_none(line_map["line_type"]),
                    "stage_direction_style_id": _zero_to_none(
                        line_map["stage_direction_style_id"]
                    ),
                    "line_parts": line_parts,
                }
            )
            get_logger().debug(
                f"extract_lines_from_ydoc: page {page_num}[{i}] "
                f"_id={raw_id!r} parts={len(line_parts)}"
            )

        lines_by_page.append({"page": page_num, "lines": lines})

    return lines_by_page, deleted_line_ids


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------


def _has_line_changed(ydoc_line: dict, db_id: int, session: DigiDBSession) -> bool:
    """Compare a Y.Doc line dict against the current DB row.

    :param ydoc_line: Extracted line dict from the Y.Doc.
    :param db_id: The integer ``ScriptLine.id`` to compare against.
    :param session: Active SQLAlchemy session.
    :returns: True if any field or part differs from the DB record.
    :raises ValueError: If *db_id* is not found in the database.
    """
    existing_line = session.scalars(
        select(ScriptLine).where(ScriptLine.id == db_id)
    ).first()
    if not existing_line:
        raise ValueError(f"Script line {db_id} not found in database.")

    if existing_line.act_id != ydoc_line["act_id"]:
        return True
    if existing_line.scene_id != ydoc_line["scene_id"]:
        return True
    line_type_val = existing_line.line_type.value if existing_line.line_type else None
    if line_type_val != ydoc_line["line_type"]:
        return True
    if existing_line.stage_direction_style_id != ydoc_line["stage_direction_style_id"]:
        return True

    existing_parts = sorted(existing_line.line_parts, key=lambda p: p.part_index or 0)
    ydoc_parts = ydoc_line["line_parts"]

    if len(existing_parts) != len(ydoc_parts):
        return True

    for ep, yp in zip(existing_parts, ydoc_parts):
        if ep.character_id != yp["character_id"]:
            return True
        if ep.character_group_id != yp["character_group_id"]:
            return True
        if (ep.line_text or "") != (yp["line_text"] or ""):
            return True
        if ep.part_index != yp["part_index"]:
            return True

    return False


# ---------------------------------------------------------------------------
# Normalise
# ---------------------------------------------------------------------------


def _ydoc_line_to_dict(ydoc_line: dict, page_number: int) -> dict:
    """Normalise a Y.Doc line dict to the format expected by ``create_new_line`` / ``validate_line``.

    :param ydoc_line: Raw line dict from ``extract_lines_from_ydoc``.
    :param page_number: The page number to inject (Y.Doc doesn't store it
        per-line; it's derived from the page key).
    :returns: A dict compatible with the REST API line format.
    """
    return {
        "act_id": ydoc_line["act_id"],
        "scene_id": ydoc_line["scene_id"],
        "page": page_number,
        "line_type": ydoc_line["line_type"],
        "stage_direction_style_id": ydoc_line["stage_direction_style_id"],
        "line_parts": [
            {
                "character_id": p["character_id"],
                "character_group_id": p["character_group_id"],
                "line_text": p["line_text"],
                "part_index": p["part_index"],
            }
            for p in ydoc_line["line_parts"]
        ],
    }


# ---------------------------------------------------------------------------
# Save
# ---------------------------------------------------------------------------


def _save_script_page(
    revision: ScriptRevision,
    page_number: int,
    page_data: list[dict],
    deleted_line_ids: list[int],
    session: DigiDBSession,
    show: Show,
    previous_line: ScriptLineRevisionAssociation | None,
) -> tuple[ScriptLineRevisionAssociation | None, dict[str, str], dict[str, str]]:
    """Persist one page of Y.Doc data to the database.

    Uses a two-pass approach that mirrors the PATCH endpoint in
    ``controllers/api/show/script/script.py``:

    **Pass 1** — Y.Doc lines in Y.Array order:
    - New lines (UUID ``_id``): validate, create ``ScriptLine`` + parts,
      record UUID→DB-id mapping for post-save Y.Doc patching.
    - Changed existing lines: validate, create new ``ScriptLine``, migrate
      ``CueAssociation`` and ``ScriptCuts``, orphan-clean old line.
    - Unchanged existing lines: update linked-list pointers only (bridges
      over gaps left by deleted lines).

    **Pass 2** — deleted lines that belong to this page:
    - Update neighbour pointers, delete ``CueAssociation`` records, delete
      the ``ScriptLineRevisionAssociation``, run orphan cleanup.

    :param revision: Target ``ScriptRevision``.
    :param page_number: Page being saved.
    :param page_data: Ordered list of Y.Doc line dicts for this page.
    :param deleted_line_ids: All deleted line DB ids (across all pages).
    :param session: Active SQLAlchemy session.
    :param show: Show model (used by the line validator).
    :param previous_line: Last association from the preceding page (or None
        for page 1).
    :returns: ``(last_assoc, new_line_id_map, new_part_id_map)`` where the
        mappings are ``{uuid_str: str(db_id)}`` for newly inserted objects.
    :raises ValueError: If line validation fails.
    """
    new_line_id_map: dict[str, str] = {}
    new_part_id_map: dict[str, str] = {}

    log = get_logger()
    log.debug(
        f"_save_script_page: revision={revision.id} page={page_number} "
        f"lines={len(page_data)} deleted_ids={deleted_line_ids}"
    )

    # ------------------------------------------------------------------
    # Pass 1: process Y.Doc lines in array order
    # ------------------------------------------------------------------
    for idx, line_data in enumerate(page_data):
        line_dict = _ydoc_line_to_dict(line_data, page_number)
        db_id = _parse_db_id(line_data["_id"])
        ydoc_id_str = str(line_data["_id"])

        if db_id is None:
            # ---- New line (UUID / 0 sentinel) ----
            log.debug(
                f"  [{idx}] NEW line ydoc_id={ydoc_id_str!r} "
                f"act={line_dict['act_id']} scene={line_dict['scene_id']} "
                f"type={line_dict['line_type']}"
            )
            is_valid, error_msg = validate_line(show, line_dict)
            if not is_valid:
                log.warning(
                    f"  [{idx}] Validation FAILED for new line ydoc_id={ydoc_id_str!r}: {error_msg}"
                )
                raise ValueError(
                    f"Line validation failed on page {page_number}: {error_msg}"
                )

            assoc, line_obj = create_new_line(
                session, revision, line_dict, previous_line
            )
            log.debug(
                f"  [{idx}] Created new ScriptLine id={line_obj.id} "
                f"(ydoc_id {ydoc_id_str!r} → db id {line_obj.id})"
            )

            # Record UUID → real DB id for Y.Doc patching after commit
            new_line_id_map[ydoc_id_str] = str(line_obj.id)
            # Record part UUIDs → real part IDs (zip preserves insertion order)
            sorted_parts = sorted(line_obj.line_parts, key=lambda p: p.part_index or 0)
            for ydoc_part, db_part in zip(line_data["line_parts"], sorted_parts):
                part_id_str = str(ydoc_part["_id"])
                if _parse_db_id(ydoc_part["_id"]) is None:
                    new_part_id_map[part_id_str] = str(db_part.id)
                    log.debug(
                        f"    part ydoc_id {part_id_str!r} → db part id {db_part.id}"
                    )

            previous_line = assoc

        else:
            # ---- Existing line ----
            curr_assoc = session.get(
                ScriptLineRevisionAssociation, (revision.id, db_id)
            )
            if curr_assoc is None:
                # This happens when a line was changed in a previous save:
                # the association's line_id was updated to a new ScriptLine,
                # but the Y.Doc still holds the old _id.
                log.warning(
                    f"  [{idx}] SKIP — no ScriptLineRevisionAssociation found for "
                    f"revision={revision.id} line_id={db_id} "
                    f"(ydoc_id={ydoc_id_str!r}). "
                    f"This line will NOT be saved. "
                    f"Likely cause: Y.Doc _id was not updated after a previous save "
                    f"that replaced this line with a new ScriptLine."
                )
                continue

            if _has_line_changed(line_data, db_id, session):
                log.debug(
                    f"  [{idx}] CHANGED existing line db_id={db_id} "
                    f"(assoc line_id={curr_assoc.line_id})"
                )
                # ---- Changed: create new ScriptLine, update assoc ----
                is_valid, error_msg = validate_line(show, line_dict)
                if not is_valid:
                    log.warning(
                        f"  [{idx}] Validation FAILED for changed line db_id={db_id}: {error_msg}"
                    )
                    raise ValueError(
                        f"Line validation failed on page {page_number}: {error_msg}"
                    )

                curr_line = curr_assoc.line
                old_line_id = curr_line.id
                _, line_object = create_new_line(
                    session, revision, line_dict, previous_line, with_association=False
                )
                log.debug(
                    f"  [{idx}] Replaced ScriptLine old_id={old_line_id} → new_id={line_object.id}. "
                    f"Y.Doc _id is still {ydoc_id_str!r} — needs patching."
                )
                curr_assoc.line = line_object
                if previous_line:
                    previous_line.next_line = line_object
                    curr_assoc.previous_line = previous_line.line
                if curr_assoc.next_line:
                    next_assoc = session.get(
                        ScriptLineRevisionAssociation,
                        (revision.id, curr_assoc.next_line.id),
                    )
                    if next_assoc:
                        next_assoc.previous_line = line_object
                session.flush()

                # Record old DB id → new DB id for Y.Doc patching after commit.
                # Without this, the Y.Doc retains the stale old _id, causing the
                # line to be silently skipped on the next save.
                new_line_id_map[ydoc_id_str] = str(line_object.id)

                # Migrate CueAssociation: old line → new line
                cue_assocs = session.scalars(
                    select(CueAssociation).where(
                        CueAssociation.revision_id == revision.id,
                        CueAssociation.line_id == curr_line.id,
                    )
                ).all()
                for old_ca in cue_assocs:
                    session.add(
                        CueAssociation(
                            revision_id=revision.id,
                            line_id=line_object.id,
                            cue_id=old_ca.cue_id,
                        )
                    )
                    session.delete(old_ca)

                # Migrate ScriptCuts: old line_parts → new line_parts
                old_parts_map = {p.part_index: p.id for p in curr_line.line_parts}
                new_parts_map = {p.part_index: p.id for p in line_object.line_parts}
                # Record old part DB ids → new part DB ids for Y.Doc patching
                for part_index, old_part_id in old_parts_map.items():
                    new_part_id = new_parts_map.get(part_index)
                    if new_part_id:
                        new_part_id_map[str(old_part_id)] = str(new_part_id)
                for part_index, old_part_id in old_parts_map.items():
                    cuts = session.scalars(
                        select(ScriptCuts).where(
                            ScriptCuts.revision_id == revision.id,
                            ScriptCuts.line_part_id == old_part_id,
                        )
                    ).all()
                    for old_cut in cuts:
                        new_part_id = new_parts_map.get(part_index)
                        if new_part_id:
                            session.add(
                                ScriptCuts(
                                    revision_id=revision.id,
                                    line_part_id=new_part_id,
                                )
                            )
                        session.delete(old_cut)

                session.flush()

                if len(curr_line.revision_associations) == 0:
                    session.delete(curr_line)
                    log.debug(
                        f"  [{idx}] Orphan-deleted old ScriptLine id={old_line_id}"
                    )
                session.flush()

                previous_line = curr_assoc

            else:
                log.debug(
                    f"  [{idx}] UNCHANGED existing line db_id={db_id} "
                    f"(pointer update only)"
                )
                # ---- Unchanged: update pointers to bridge deleted-line gaps ----
                if previous_line:
                    previous_line.next_line = curr_assoc.line
                curr_assoc.previous_line = previous_line.line if previous_line else None
                session.flush()
                previous_line = curr_assoc

    log.debug(
        f"_save_script_page: page={page_number} pass1 done. "
        f"new_line_id_map={new_line_id_map} new_part_id_map keys={list(new_part_id_map.keys())}"
    )

    # ------------------------------------------------------------------
    # Pass 2: delete lines marked as deleted that belong to this page
    # ------------------------------------------------------------------
    # Guard: do not delete a line that was just created in Pass 1.
    # This can happen if SQLite reuses an integer ID that is still present
    # in a stale deleted_line_ids entry from a previous save.
    newly_created_ids = {int(v) for v in new_line_id_map.values()}
    for deleted_id in deleted_line_ids:
        if deleted_id in newly_created_ids:
            log.warning(
                f"  [del] Skipping stale deleted_id={deleted_id} — "
                f"just created in Pass 1 (stale deleted_line_ids entry)"
            )
            continue
        line = session.get(ScriptLine, deleted_id)
        if not line or line.page != page_number:
            log.debug(
                f"  [del] Skipping deleted_id={deleted_id}: "
                f"line={'not found' if not line else f'page={line.page} != {page_number}'}"
            )
            continue
        assoc = session.get(ScriptLineRevisionAssociation, (revision.id, deleted_id))
        if not assoc:
            log.warning(
                f"  [del] No association found for deleted line id={deleted_id} "
                f"revision={revision.id} — already removed?"
            )
            continue
        log.debug(f"  [del] Deleting line id={deleted_id} from page {page_number}")

        # Update next/previous neighbour pointers (mirrors script.py:491–540)
        if assoc.next_line and assoc.previous_line:
            next_assoc = session.get(
                ScriptLineRevisionAssociation, (revision.id, assoc.next_line.id)
            )
            prev_assoc = session.get(
                ScriptLineRevisionAssociation, (revision.id, assoc.previous_line.id)
            )
            if next_assoc:
                next_assoc.previous_line = assoc.previous_line
                session.flush()
            if prev_assoc:
                prev_assoc.next_line = next_assoc.line if next_assoc else None
                session.flush()
        elif assoc.next_line:
            next_assoc = session.get(
                ScriptLineRevisionAssociation, (revision.id, assoc.next_line.id)
            )
            if next_assoc:
                next_assoc.previous_line = None
                session.flush()
        elif assoc.previous_line:
            prev_assoc = session.get(
                ScriptLineRevisionAssociation, (revision.id, assoc.previous_line.id)
            )
            if prev_assoc:
                prev_assoc.next_line = None
                session.flush()

        line_id_to_cleanup = assoc.line_id

        # Delete revision-scoped CueAssociation records for this line
        cue_assocs = session.scalars(
            select(CueAssociation).where(
                CueAssociation.revision_id == revision.id,
                CueAssociation.line_id == line_id_to_cleanup,
            )
        ).all()
        cue_ids_to_cleanup = [ca.cue_id for ca in cue_assocs]
        for ca in cue_assocs:
            session.delete(ca)

        session.delete(assoc)

        # Orphan cleanup (mirrors script.py:561–565)
        ScriptLineRevisionAssociation.cleanup_orphaned_line(session, line_id_to_cleanup)
        for cue_id in cue_ids_to_cleanup:
            CueAssociation.cleanup_orphaned_cue(session, cue_id)

    log.debug(
        f"_save_script_page: page={page_number} complete. "
        f"previous_line={previous_line.line_id if previous_line else None}"
    )
    return previous_line, new_line_id_map, new_part_id_map
