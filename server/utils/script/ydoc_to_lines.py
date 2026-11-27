"""Convert a pycrdt Y.Doc back to database ScriptLine records.

Entry points
------------
- ``extract_lines_from_ydoc`` — read Y.Doc into plain Python data (fast, sync)
- ``_save_script_page`` — persist one page of Y.Doc data to the DB (called by
  ``ScriptRoom.save_draft``)
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
from utils.script.line_to_ydoc import numeric_page_keys


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


def _resolve_alias(raw, id_aliases: dict[str, str]) -> str:
    """Follow a chain of id rewrites (UUID -> DB id -> newer DB id) to the current id.

    A client that has not yet received a save's id patch records a deletion against
    the id it still knows; the room remembers every rewrite so that is not lost.
    """
    seen = set()
    key = str(raw)
    while key in id_aliases and key not in seen:
        seen.add(key)
        key = id_aliases[key]
    return key


def _collect_deleted_line_ids(
    deleted_arr: pycrdt.Array, id_aliases: dict[str, str] | None
) -> list[int]:
    """Read the ``deleted_line_ids`` array, resolving aliases and skipping UUIDs.

    UUIDs are lines that were never saved to the DB, so there is nothing to delete.
    """
    deleted_line_ids: list[int] = []
    for i in range(len(deleted_arr)):
        raw = _resolve_alias(deleted_arr[i], id_aliases or {})
        db_id = _parse_db_id(raw)
        if db_id is not None:
            deleted_line_ids.append(db_id)
        else:
            get_logger().debug(
                f"extract_lines_from_ydoc: skipping non-DB deleted_line_id {raw!r}"
            )
    return deleted_line_ids


def _validated_page_keys(pages_map: pycrdt.Map) -> list[str]:
    """Return the numeric page keys, sorted, after checking the draft is well formed.

    :raises ValueError: If non-page keys hold content, or a page is not a Y.Array.
    """
    page_keys = sorted(numeric_page_keys(pages_map), key=int)
    ignored = sorted(set(pages_map.keys()) - set(page_keys))
    for key in ignored:
        content = pages_map[key]
        if isinstance(content, (pycrdt.Array, pycrdt.Map)) and len(content) > 0:
            # Ignoring it would drop the content while the save reports success and
            # the draft is deleted, so fail the save (and keep the draft) instead.
            raise ValueError(
                f"Draft has content under the non-page key {key!r}; refusing to save "
                f"and silently drop it"
            )
        get_logger().debug(
            f"extract_lines_from_ydoc: ignoring empty non-page key {key!r}"
        )
    for key in page_keys:
        if not isinstance(pages_map[key], pycrdt.Array):
            raise ValueError(f"Page {key} is not a Y.Array; the draft is malformed")
    return page_keys


def _extract_part(part_map, position: int) -> dict:
    """Read one line part from its Y.Map.

    ``part_index`` is the part's *position*, not the stored value: two editors
    appending a part concurrently both write the same index, and array order is
    the one thing Yjs converges on.
    """
    return {
        "_id": part_map["_id"],
        "part_index": position,
        "character_id": _zero_to_none(part_map["character_id"]),
        "character_group_id": _zero_to_none(part_map["character_group_id"]),
        "line_text": str(part_map["line_text"]),
    }


def _extract_line(line_map) -> dict:
    """Read one script line (and its parts) from its Y.Map."""
    parts_array = line_map["parts"]
    return {
        "_id": line_map["_id"],
        "act_id": _zero_to_none(line_map["act_id"]),
        "scene_id": _zero_to_none(line_map["scene_id"]),
        "line_type": _zero_to_none(line_map["line_type"]),
        "stage_direction_style_id": _zero_to_none(line_map["stage_direction_style_id"]),
        "line_parts": [
            _extract_part(parts_array[j], j) for j in range(len(parts_array))
        ],
    }


def _extract_page(page_num: int, page_array: pycrdt.Array) -> dict:
    """Read every line on one page into ``{"page": int, "lines": [...]}``."""
    get_logger().debug(
        f"extract_lines_from_ydoc: page {page_num} has {len(page_array)} line(s)"
    )
    lines: list[dict] = []
    for i in range(len(page_array)):
        line = _extract_line(page_array[i])
        lines.append(line)
        get_logger().debug(
            f"extract_lines_from_ydoc: page {page_num}[{i}] "
            f"_id={line['_id']!r} parts={len(line['line_parts'])}"
        )
    return {"page": page_num, "lines": lines}


def extract_lines_from_ydoc(
    doc: pycrdt.Doc,
    id_aliases: dict[str, str] | None = None,
) -> tuple[list[dict], list[int]]:
    """Read the Y.Doc and return plain Python data.

    MUST run synchronously in the event loop (not in an executor) to ensure a
    consistent point-in-time snapshot.

    :param doc: The pycrdt Y.Doc to extract from.
    :param id_aliases: Optional ``{old_id: new_id}`` record of ids earlier saves have
        rewritten, used to resolve deletions recorded against a stale id.
    :returns: ``(lines_by_page, deleted_line_ids)`` where ``lines_by_page`` is
        a list of ``{"page": int, "lines": list[dict]}`` dicts ordered by page
        number, and ``deleted_line_ids`` is a list of integer DB ids of lines
        that were deleted by editors.
    :raises ValueError: If the draft is malformed (see ``_validated_page_keys``).
    """
    pages_map = doc.get("pages", type=pycrdt.Map)
    deleted_arr = doc.get("deleted_line_ids", type=pycrdt.Array)

    deleted_line_ids = _collect_deleted_line_ids(deleted_arr, id_aliases)
    get_logger().debug(f"extract_lines_from_ydoc: deleted_line_ids={deleted_line_ids}")

    page_keys = _validated_page_keys(pages_map)
    get_logger().debug(
        f"extract_lines_from_ydoc: {len(page_keys)} page(s): {page_keys}"
    )

    lines_by_page = [_extract_page(int(key), pages_map[key]) for key in page_keys]
    return lines_by_page, deleted_line_ids


# ---------------------------------------------------------------------------
# Change detection
# ---------------------------------------------------------------------------


def _has_line_changed(
    ydoc_line: dict, db_id: int, page_number: int, session: DigiDBSession
) -> bool:
    """Compare a Y.Doc line dict against the current DB row.

    :param ydoc_line: Extracted line dict from the Y.Doc.
    :param db_id: The integer ``ScriptLine.id`` to compare against.
    :param page_number: The page the line currently sits on in the Y.Doc.
    :param session: Active SQLAlchemy session.
    :returns: True if any field or part differs from the DB record.
    :raises ValueError: If *db_id* is not found in the database.
    """
    existing_line = session.scalars(
        select(ScriptLine).where(ScriptLine.id == db_id)
    ).first()
    if not existing_line:
        raise ValueError(f"Script line {db_id} not found in database.")

    if _line_fields_differ(existing_line, ydoc_line, page_number):
        return True

    existing_parts = sorted(existing_line.line_parts, key=lambda p: p.part_index or 0)
    ydoc_parts = ydoc_line["line_parts"]
    if len(existing_parts) != len(ydoc_parts):
        return True
    return any(_part_differs(ep, yp) for ep, yp in zip(existing_parts, ydoc_parts))


def _line_fields_differ(existing_line, ydoc_line: dict, page_number: int) -> bool:
    """True if any top-level field of the DB line differs from the Y.Doc line."""
    line_type_val = existing_line.line_type.value if existing_line.line_type else None
    return (
        existing_line.page,
        existing_line.act_id,
        existing_line.scene_id,
        line_type_val,
        existing_line.stage_direction_style_id,
    ) != (
        page_number,
        ydoc_line["act_id"],
        ydoc_line["scene_id"],
        ydoc_line["line_type"],
        ydoc_line["stage_direction_style_id"],
    )


def _part_differs(existing_part, ydoc_part: dict) -> bool:
    """True if a DB line part differs from the matching Y.Doc part."""
    return (
        existing_part.character_id,
        existing_part.character_group_id,
        existing_part.line_text or "",
        existing_part.part_index,
    ) != (
        ydoc_part["character_id"],
        ydoc_part["character_group_id"],
        ydoc_part["line_text"] or "",
        ydoc_part["part_index"],
    )


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


@dataclass
class _PageSaveContext:
    """Shared state for saving one page of Y.Doc data (see ``_save_script_page``)."""

    revision: ScriptRevision
    page_number: int
    session: DigiDBSession
    show: Show
    changed_pages: set[int]
    new_line_id_map: dict[str, str] = field(default_factory=dict)
    new_part_id_map: dict[str, str] = field(default_factory=dict)


def _validate_or_raise(
    ctx: _PageSaveContext, idx: int, line_dict: dict, description: str
) -> None:
    """Validate a line dict, raising ``ValueError`` on failure.

    :param ctx: Page save context.
    :param idx: Index of the line within the page (for logging).
    :param line_dict: Line data as built by ``_ydoc_line_to_dict``.
    :param description: Human-readable line description for the warning log.
    :raises ValueError: If line validation fails.
    """
    is_valid, error_msg = validate_line(ctx.show, line_dict)
    if not is_valid:
        get_logger().warning(
            f"  [{idx}] Validation FAILED for {description}: {error_msg}"
        )
        raise ValueError(
            f"Line validation failed on page {ctx.page_number}: {error_msg}"
        )


def _save_new_line(
    ctx: _PageSaveContext,
    idx: int,
    line_data: dict,
    line_dict: dict,
    ydoc_id_str: str,
    previous_line: ScriptLineRevisionAssociation | None,
) -> ScriptLineRevisionAssociation:
    """Create a ``ScriptLine`` for a Y.Doc line that has no DB id yet.

    :returns: The new line's association (the next ``previous_line``).
    :raises ValueError: If line validation fails.
    """
    log = get_logger()
    log.debug(
        f"  [{idx}] NEW line ydoc_id={ydoc_id_str!r} "
        f"act={line_dict['act_id']} scene={line_dict['scene_id']} "
        f"type={line_dict['line_type']}"
    )
    _validate_or_raise(ctx, idx, line_dict, f"new line ydoc_id={ydoc_id_str!r}")

    assoc, line_obj = create_new_line(
        ctx.session, ctx.revision, line_dict, previous_line
    )
    ctx.changed_pages.add(ctx.page_number)
    log.debug(
        f"  [{idx}] Created new ScriptLine id={line_obj.id} "
        f"(ydoc_id {ydoc_id_str!r} → db id {line_obj.id})"
    )

    # Record UUID → real DB id for Y.Doc patching after commit
    ctx.new_line_id_map[ydoc_id_str] = str(line_obj.id)
    # Record part UUIDs → real part IDs (zip preserves insertion order)
    sorted_parts = sorted(line_obj.line_parts, key=lambda p: p.part_index or 0)
    for ydoc_part, db_part in zip(line_data["line_parts"], sorted_parts):
        part_id_str = str(ydoc_part["_id"])
        if _parse_db_id(ydoc_part["_id"]) is None:
            ctx.new_part_id_map[part_id_str] = str(db_part.id)
            log.debug(f"    part ydoc_id {part_id_str!r} → db part id {db_part.id}")
    return assoc


def _migrate_cue_associations(
    ctx: _PageSaveContext, old_line_id: int, new_line_id: int
) -> None:
    """Move this revision's ``CueAssociation`` rows from the old line to the new."""
    session = ctx.session
    cue_assocs = session.scalars(
        select(CueAssociation).where(
            CueAssociation.revision_id == ctx.revision.id,
            CueAssociation.line_id == old_line_id,
        )
    ).all()
    for old_ca in cue_assocs:
        session.add(
            CueAssociation(
                revision_id=ctx.revision.id,
                line_id=new_line_id,
                cue_id=old_ca.cue_id,
                group_id=old_ca.group_id,
                sort_order=old_ca.sort_order,
            )
        )
        session.delete(old_ca)


def _migrate_script_cuts(
    ctx: _PageSaveContext, old_line: ScriptLine, new_line: ScriptLine
) -> None:
    """Move ``ScriptCuts`` from the old line's parts to the new line's parts.

    Also records old part DB id → new part DB id in ``ctx.new_part_id_map`` for
    Y.Doc patching after commit.
    """
    session = ctx.session
    old_parts_map = {p.part_index: p.id for p in old_line.line_parts}
    new_parts_map = {p.part_index: p.id for p in new_line.line_parts}
    for part_index, old_part_id in old_parts_map.items():
        new_part_id = new_parts_map.get(part_index)
        if new_part_id:
            ctx.new_part_id_map[str(old_part_id)] = str(new_part_id)
    for part_index, old_part_id in old_parts_map.items():
        new_part_id = new_parts_map.get(part_index)
        cuts = session.scalars(
            select(ScriptCuts).where(
                ScriptCuts.revision_id == ctx.revision.id,
                ScriptCuts.line_part_id == old_part_id,
            )
        ).all()
        for old_cut in cuts:
            if new_part_id:
                session.add(
                    ScriptCuts(
                        revision_id=ctx.revision.id,
                        line_part_id=new_part_id,
                    )
                )
            session.delete(old_cut)


def _save_changed_line(
    ctx: _PageSaveContext,
    idx: int,
    line_dict: dict,
    ydoc_id_str: str,
    db_id: int,
    curr_assoc: ScriptLineRevisionAssociation,
    previous_line: ScriptLineRevisionAssociation | None,
) -> ScriptLineRevisionAssociation:
    """Replace an edited existing line with a new ``ScriptLine``.

    Creates the new line, re-points the association and linked-list neighbours,
    migrates cues and cuts, and orphan-deletes the old line.

    :returns: The updated association (the next ``previous_line``).
    :raises ValueError: If line validation fails.
    """
    session = ctx.session
    log = get_logger()
    log.debug(
        f"  [{idx}] CHANGED existing line db_id={db_id} "
        f"(assoc line_id={curr_assoc.line_id})"
    )
    _validate_or_raise(ctx, idx, line_dict, f"changed line db_id={db_id}")

    curr_line = curr_assoc.line
    old_line_id = curr_line.id
    ctx.changed_pages.add(ctx.page_number)
    # A line moved between pages leaves its old page too. `page` is
    # nullable on legacy rows; a NULL is not a page anyone can be told about.
    if curr_line.page is not None:
        ctx.changed_pages.add(curr_line.page)
    _, line_object = create_new_line(
        session, ctx.revision, line_dict, previous_line, with_association=False
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
            (ctx.revision.id, curr_assoc.next_line.id),
        )
        if next_assoc:
            next_assoc.previous_line = line_object
    session.flush()

    # Record old DB id → new DB id for Y.Doc patching after commit.
    # Without this, the Y.Doc retains the stale old _id, causing the
    # line to be silently skipped on the next save.
    ctx.new_line_id_map[ydoc_id_str] = str(line_object.id)

    _migrate_cue_associations(ctx, curr_line.id, line_object.id)
    _migrate_script_cuts(ctx, curr_line, line_object)
    session.flush()

    if len(curr_line.revision_associations) == 0:
        session.delete(curr_line)
        log.debug(f"  [{idx}] Orphan-deleted old ScriptLine id={old_line_id}")
    session.flush()
    return curr_assoc


def _save_unchanged_line(
    ctx: _PageSaveContext,
    idx: int,
    db_id: int,
    curr_assoc: ScriptLineRevisionAssociation,
    previous_line: ScriptLineRevisionAssociation | None,
) -> ScriptLineRevisionAssociation:
    """Update linked-list pointers only, bridging gaps left by deleted lines.

    :returns: The association (the next ``previous_line``).
    """
    get_logger().debug(
        f"  [{idx}] UNCHANGED existing line db_id={db_id} (pointer update only)"
    )
    if previous_line:
        previous_line.next_line = curr_assoc.line
    curr_assoc.previous_line = previous_line.line if previous_line else None
    ctx.session.flush()
    return curr_assoc


def _save_existing_line(
    ctx: _PageSaveContext,
    idx: int,
    line_dict: dict,
    ydoc_id_str: str,
    db_id: int,
    line_data: dict,
    previous_line: ScriptLineRevisionAssociation | None,
) -> ScriptLineRevisionAssociation | None:
    """Save a Y.Doc line that already has a DB id (changed or unchanged).

    :returns: The next ``previous_line`` (unchanged if the line is skipped).
    :raises ValueError: If a changed line fails validation.
    """
    revision = ctx.revision
    curr_assoc = ctx.session.get(ScriptLineRevisionAssociation, (revision.id, db_id))
    if curr_assoc is None:
        # This happens when a line was changed in a previous save:
        # the association's line_id was updated to a new ScriptLine,
        # but the Y.Doc still holds the old _id.
        get_logger().warning(
            f"  [{idx}] SKIP — no ScriptLineRevisionAssociation found for "
            f"revision={revision.id} line_id={db_id} "
            f"(ydoc_id={ydoc_id_str!r}). "
            f"This line will NOT be saved. "
            f"Likely cause: Y.Doc _id was not updated after a previous save "
            f"that replaced this line with a new ScriptLine."
        )
        return previous_line

    if _has_line_changed(line_data, db_id, ctx.page_number, ctx.session):
        return _save_changed_line(
            ctx, idx, line_dict, ydoc_id_str, db_id, curr_assoc, previous_line
        )
    return _save_unchanged_line(ctx, idx, db_id, curr_assoc, previous_line)


def _unlink_deleted_neighbours(
    ctx: _PageSaveContext, assoc: ScriptLineRevisionAssociation
) -> None:
    """Update next/previous neighbour pointers around a line being deleted.

    Mirrors script.py:491–540.
    """
    session = ctx.session
    revision_id = ctx.revision.id
    next_assoc = None
    prev_assoc = None
    if assoc.next_line:
        next_assoc = session.get(
            ScriptLineRevisionAssociation, (revision_id, assoc.next_line.id)
        )
    if assoc.previous_line:
        prev_assoc = session.get(
            ScriptLineRevisionAssociation, (revision_id, assoc.previous_line.id)
        )

    if assoc.next_line and assoc.previous_line:
        if next_assoc:
            next_assoc.previous_line = assoc.previous_line
            session.flush()
        if prev_assoc:
            prev_assoc.next_line = next_assoc.line if next_assoc else None
            session.flush()
    elif assoc.next_line:
        if next_assoc:
            next_assoc.previous_line = None
            session.flush()
    elif assoc.previous_line:
        if prev_assoc:
            prev_assoc.next_line = None
            session.flush()


def _delete_line_association(
    ctx: _PageSaveContext, assoc: ScriptLineRevisionAssociation
) -> None:
    """Delete a line's cue associations and association row, then orphan-clean."""
    session = ctx.session
    line_id_to_cleanup = assoc.line_id

    # no_autoflush: prevents lazy loading triggered during orphan cleanup from
    # flushing this deletion mid-cascade (see CLAUDE.md cascade deletion pattern).
    with session.no_autoflush:
        # Delete revision-scoped CueAssociation records for this line
        cue_assocs = session.scalars(
            select(CueAssociation).where(
                CueAssociation.revision_id == ctx.revision.id,
                CueAssociation.line_id == line_id_to_cleanup,
            )
        ).all()
        cue_ids_to_cleanup = [ca.cue_id for ca in cue_assocs]
        for ca in cue_assocs:
            session.delete(ca)

        session.delete(assoc)

        # Orphan cleanup (mirrors the delete-path pointer/orphan cleanup in
        # script.py's PATCH handler)
        ScriptLineRevisionAssociation.cleanup_orphaned_line(session, line_id_to_cleanup)
        for cue_id in cue_ids_to_cleanup:
            CueAssociation.cleanup_orphaned_cue(session, cue_id)


def _delete_marked_lines(ctx: _PageSaveContext, deleted_line_ids: list[int]) -> None:
    """Pass 2: delete lines marked as deleted that belong to this page."""
    session = ctx.session
    log = get_logger()
    page_number = ctx.page_number
    # Guard: do not delete a line that was just created in Pass 1.
    # This can happen if SQLite reuses an integer ID that is still present
    # in a stale deleted_line_ids entry from a previous save.
    newly_created_ids = {int(v) for v in ctx.new_line_id_map.values()}
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
        assoc = session.get(
            ScriptLineRevisionAssociation, (ctx.revision.id, deleted_id)
        )
        if not assoc:
            log.warning(
                f"  [del] No association found for deleted line id={deleted_id} "
                f"revision={ctx.revision.id} — already removed?"
            )
            continue
        log.debug(f"  [del] Deleting line id={deleted_id} from page {page_number}")
        ctx.changed_pages.add(page_number)

        _unlink_deleted_neighbours(ctx, assoc)
        _delete_line_association(ctx, assoc)


def _save_script_page(
    revision: ScriptRevision,
    page_number: int,
    page_data: list[dict],
    deleted_line_ids: list[int],
    session: DigiDBSession,
    show: Show,
    previous_line: ScriptLineRevisionAssociation | None,
    changed_pages: set[int] | None = None,
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
    :param changed_pages: Optional set that every page whose DB content this call
        altered (a line created, replaced or deleted) is added to, so the caller can
        notify clients about only those pages.
    :returns: ``(last_assoc, new_line_id_map, new_part_id_map)`` where the
        mappings are ``{uuid_str: str(db_id)}`` for newly inserted objects.
    :raises ValueError: If line validation fails.
    """
    ctx = _PageSaveContext(
        revision=revision,
        page_number=page_number,
        session=session,
        show=show,
        changed_pages=changed_pages if changed_pages is not None else set(),
    )

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
            previous_line = _save_new_line(
                ctx, idx, line_data, line_dict, ydoc_id_str, previous_line
            )
        else:
            previous_line = _save_existing_line(
                ctx, idx, line_dict, ydoc_id_str, db_id, line_data, previous_line
            )

    log.debug(
        f"_save_script_page: page={page_number} pass1 done. "
        f"new_line_id_map={ctx.new_line_id_map} "
        f"new_part_id_map keys={list(ctx.new_part_id_map.keys())}"
    )

    # ------------------------------------------------------------------
    # Pass 2: delete lines marked as deleted that belong to this page
    # ------------------------------------------------------------------
    _delete_marked_lines(ctx, deleted_line_ids)

    log.debug(
        f"_save_script_page: page={page_number} complete. "
        f"previous_line={previous_line.line_id if previous_line else None}"
    )
    return previous_line, ctx.new_line_id_map, ctx.new_part_id_map
