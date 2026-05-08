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
            or (d["prev_page"] is not None and d["prev_page"] == page - 1)
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
