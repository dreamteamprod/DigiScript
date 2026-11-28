"""Shared SQL helpers for ScriptLineRevisionAssociation repair migrations.

Both c2f8d4a6e0b3 and 897ae2963f6d use these primitives; they differ only in
how they select the bridge (first) line when multiple candidates exist for a page.
"""

from collections import defaultdict
from typing import Callable

import sqlalchemy as sa


def fetch_page_associations(conn, revision_id: int) -> dict:
    """Return ``{page: {line_id: {next, prev, prev_page}}}`` for one revision."""
    rows = conn.execute(
        sa.text(
            """
            SELECT a.line_id, a.next_line_id, a.previous_line_id,
                   l.page  AS line_page,
                   lp.page AS prev_page
            FROM script_line_revision_association a
            JOIN script_lines l  ON l.id  = a.line_id
            LEFT JOIN script_lines lp ON lp.id = a.previous_line_id
            WHERE a.revision_id = :rev_id
            """
        ),
        {"rev_id": revision_id},
    ).fetchall()

    by_page: dict = defaultdict(dict)
    for row in rows:
        line_id, next_id, prev_id, page, prev_page = row
        by_page[page if page is not None else 0][line_id] = {
            "next": next_id,
            "prev": prev_id,
            "prev_page": prev_page,
        }
    return by_page


def build_page_ordered(by_page: dict, pick_bridge: Callable) -> dict:
    """Build ``{page: [line_id, ...]}`` using bridge detection.

    :param by_page: Output of :func:`fetch_page_associations`.
    :param pick_bridge: ``(candidates: list[int]) -> int`` — selects the bridge
        (first) line from a non-empty list of candidates.  Pass ``max`` to use
        the highest line_id (correct for the post-corruption case) or
        ``lambda c: c[0]`` to replicate the original first-found behaviour.
    """
    result = {}
    for page in sorted(by_page.keys()):
        page_lines = by_page[page]
        candidates = [
            lid
            for lid, d in page_lines.items()
            if d["prev"] is None
            # Strictly earlier, not `== page - 1`: a page with zero lines left
            # (e.g. every line on it was deleted) is a normal gap, not
            # corruption — the next real page's first line's previous_line is
            # then on some earlier page, not literally page - 1.
            or (d["prev_page"] is not None and d["prev_page"] < page)
        ]
        if not candidates:
            result[page] = []
            continue

        first_line_id = pick_bridge(candidates)
        ordered = []
        current = first_line_id
        seen: set = set()
        while current is not None and current in page_lines:
            if current in seen:
                break
            seen.add(current)
            ordered.append(current)
            current = page_lines[current]["next"]
        result[page] = ordered
    return result


def build_global_order(page_ordered: dict) -> list:
    """Flatten ``{page: [line_id, ...]}`` into a single ordered list."""
    global_order = []
    for page in sorted(page_ordered.keys()):
        global_order.extend(page_ordered[page])
    return global_order


def compute_expected_pointers(global_order: list) -> dict:
    """Return ``{line_id: (expected_next, expected_prev)}`` for the full chain."""
    return {
        line_id: (
            global_order[i + 1] if i + 1 < len(global_order) else None,
            global_order[i - 1] if i > 0 else None,
        )
        for i, line_id in enumerate(global_order)
    }


def fetch_current_pointers(conn, revision_id: int) -> dict:
    """Return ``{line_id: (next_line_id, previous_line_id)}`` from the DB."""
    rows = conn.execute(
        sa.text(
            "SELECT line_id, next_line_id, previous_line_id "
            "FROM script_line_revision_association WHERE revision_id = :rev_id"
        ),
        {"rev_id": revision_id},
    ).fetchall()
    return {row[0]: (row[1], row[2]) for row in rows}


def collect_pointer_updates(
    expected: dict, current_by_id: dict, revision_id: int
) -> list:
    """Return list of ``(new_next, new_prev, revision_id, line_id)`` tuples that need updating."""
    updates = []
    for line_id, (exp_next, exp_prev) in expected.items():
        curr_next, curr_prev = current_by_id.get(line_id, (None, None))
        if curr_next != exp_next or curr_prev != exp_prev:
            updates.append((exp_next, exp_prev, revision_id, line_id))
    return updates


def delete_orphan_associations(conn, revision_id: int, orphan_ids) -> None:
    """Delete cue and revision associations for orphaned lines (FK order)."""
    for orphan_id in sorted(orphan_ids):
        conn.execute(
            sa.text(
                "DELETE FROM script_cue_association "
                "WHERE revision_id = :rev_id AND line_id = :line_id"
            ),
            {"rev_id": revision_id, "line_id": orphan_id},
        )
    for orphan_id in sorted(orphan_ids):
        conn.execute(
            sa.text(
                "DELETE FROM script_line_revision_association "
                "WHERE revision_id = :rev_id AND line_id = :line_id"
            ),
            {"rev_id": revision_id, "line_id": orphan_id},
        )


def apply_pointer_updates(conn, updates: list) -> None:
    """Execute UPDATE statements for all pointer corrections."""
    for new_next, new_prev, rev_id, line_id in updates:
        conn.execute(
            sa.text(
                "UPDATE script_line_revision_association "
                "SET next_line_id = :next_id, previous_line_id = :prev_id "
                "WHERE revision_id = :rev_id AND line_id = :line_id"
            ),
            {
                "next_id": new_next,
                "prev_id": new_prev,
                "rev_id": rev_id,
                "line_id": line_id,
            },
        )


def fetch_all_revision_ids(conn) -> list:
    """Return all script revision IDs in ascending order."""
    return [
        row[0]
        for row in conn.execute(
            sa.text("SELECT id FROM script_revisions ORDER BY id")
        ).fetchall()
    ]


def delete_orphaned_lines_and_parts(conn, orphan_ids) -> None:
    """Delete script_line_cuts, script_line_parts and script_lines rows that no
    longer have any revision association at all, for a set of ids just
    orphaned by a repair.

    Cuts and parts first (FK children), then the line. ``script_line_cuts``
    (``ScriptCuts``) is revision-scoped by ``line_part_id`` — CLAUDE.md's
    "Script Revision System" section lists it as a reference that must be
    checked before line deletion — and the ORM's own ``cascade="all,
    delete-orphan"`` on ``ScriptLinePart.line_part_cuts`` only fires through a
    session, never through these migrations' raw ``sa.text()`` DELETEs, so it
    has to be handled explicitly here. A no-op when *orphan_ids* is empty, so
    callers for whom a given corruption vector never produces true orphans
    (only wrong pointers on rows that still belong to a real page) can call
    this unconditionally.
    """
    for orphan_id in sorted(orphan_ids):
        conn.execute(
            sa.text(
                "DELETE FROM script_line_cuts WHERE line_part_id IN ("
                "  SELECT id FROM script_line_parts WHERE line_id = :line_id"
                ")"
            ),
            {"line_id": orphan_id},
        )
    for orphan_id in sorted(orphan_ids):
        conn.execute(
            sa.text(
                "DELETE FROM script_line_parts WHERE line_id = :line_id "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM script_line_revision_association "
                "  WHERE line_id = :line_id"
                ")"
            ),
            {"line_id": orphan_id},
        )
    for orphan_id in sorted(orphan_ids):
        conn.execute(
            sa.text(
                "DELETE FROM script_lines WHERE id = :line_id "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM script_line_revision_association "
                "  WHERE line_id = :line_id"
                ")"
            ),
            {"line_id": orphan_id},
        )


def _reachable_via_stored_chain(current_by_id: dict) -> set:
    """All line_ids reachable by walking the association table's own, already
    -stored ``next_line_id`` pointers — not the page-local reconstruction.

    Used as a safety net in :func:`repair_revision_max_bridge`: the page-walk
    can fail to place a line it has no corruption-related reason to doubt (a
    page emptied by ordinary editing, leaving a gap the bridge predicate
    doesn't bridge across) — in which case the stored chain, untouched, still
    correctly reaches it. A line reachable here must never be treated as an
    orphan, even when the page walk couldn't place it.

    Walks from every "head" — not just the one true head (``previous_line_id
    is None``), but also any line whose ``previous_line_id`` doesn't resolve
    to another row in this revision — so a revision with more than one
    disconnected, already-broken fragment still reports everything each
    fragment's own stored pointers actually reach.
    """
    starts = [
        lid
        for lid, (_, prev) in current_by_id.items()
        if prev is None or prev not in current_by_id
    ]
    reachable: set = set()
    for start in starts:
        current = start
        while current is not None and current not in reachable:
            if current not in current_by_id:
                break
            reachable.add(current)
            current = current_by_id[current][0]
    return reachable


def repair_revision_max_bridge(conn, revision_id: int) -> dict:
    """Repair linked-list pointers and remove orphans for one revision.

    Uses the max-bridge page walk: when several associations on a page both
    satisfy the "first line of this page" condition, the highest line_id is
    the correct one — every PATCH/save creates a new ScriptLine with a higher
    id than the one it replaces, so the newest row is always the live content.
    Shared by every repair migration from 897ae2963f6d onwards; they differ
    only in *why* a revision's pointers might be wrong, not in how to rebuild
    them, since the page-local bridge walk never depends on the broken global
    chain in the first place.

    If the page walk fails to place an association that the *existing* stored
    chain can still reach (see :func:`_reachable_via_stored_chain`), this
    revision is left completely untouched rather than guessing — deleting a
    line the stored chain can still reach would destroy real content, not
    repair corruption.

    :returns: Summary dict with counts of changes applied.
    """
    page_ordered = build_page_ordered(fetch_page_associations(conn, revision_id), max)
    global_order = build_global_order(page_ordered)
    current_by_id = fetch_current_pointers(conn, revision_id)
    reachable_set = set(global_order)
    unreached = set(current_by_id.keys()) - reachable_set

    unsafe = unreached & _reachable_via_stored_chain(current_by_id)
    if unsafe:
        print(
            f"  Revision {revision_id}: SKIPPED — {len(unsafe)} association(s) "
            f"{sorted(unsafe)} are reachable via the existing next_line_id "
            f"chain but not via page-local reconstruction (e.g. a page emptied "
            f"in the middle of the script). Deleting them would destroy real "
            f"content, so this revision was left untouched; it needs manual "
            f"review instead of automatic repair."
        )
        return {
            "revision_id": revision_id,
            "total": len(current_by_id),
            "pointer_updates": 0,
            "orphans_deleted": 0,
        }

    expected = compute_expected_pointers(global_order)
    updates = collect_pointer_updates(expected, current_by_id, revision_id)
    orphan_ids = unreached

    if orphan_ids:
        delete_orphan_associations(conn, revision_id, orphan_ids)
    if updates:
        apply_pointer_updates(conn, updates)
    if orphan_ids:
        delete_orphaned_lines_and_parts(conn, orphan_ids)

    return {
        "revision_id": revision_id,
        "total": len(current_by_id),
        "pointer_updates": len(updates),
        "orphans_deleted": len(orphan_ids),
    }


def run_max_bridge_repair(conn, pass_label: str) -> None:
    """Run :func:`repair_revision_max_bridge` across every revision, with
    progress output. The ``upgrade()`` body shared by every max-bridge repair
    migration; *pass_label* names the pass in the printed output only.
    """
    print(f"Repairing ScriptLineRevisionAssociation linked lists ({pass_label})…")
    revision_ids = fetch_all_revision_ids(conn)
    total_updates = 0
    total_orphans = 0
    for rev_id in revision_ids:
        result = repair_revision_max_bridge(conn, rev_id)
        if result["pointer_updates"] or result["orphans_deleted"]:
            print(
                f"  Revision {rev_id}: {result['pointer_updates']} pointer fix(es), "
                f"{result['orphans_deleted']} orphan(s) deleted "
                f"(of {result['total']} associations)"
            )
        total_updates += result["pointer_updates"]
        total_orphans += result["orphans_deleted"]
    print(
        f"Repair complete: {total_updates} pointer fix(es), "
        f"{total_orphans} orphan(s) deleted across {len(revision_ids)} revision(s)."
    )
