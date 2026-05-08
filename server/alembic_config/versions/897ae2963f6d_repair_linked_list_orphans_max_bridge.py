"""repair_linked_list_orphans_max_bridge

Revision ID: 897ae2963f6d
Revises: d2e0b8414d17
Create Date: 2026-05-08 20:37:12.115558

Repairs broken ScriptLineRevisionAssociation linked lists and removes orphaned
script_lines / script_line_parts records.

This supersedes the earlier c2f8d4a6e0b3 repair migration by fixing a bug in
bridge-line selection: when multiple associations for the same page both satisfy
the "first-line" condition (i.e. their previous_line is on page N-1), the old
migration picked whichever came first in dict-iteration order (non-deterministic).

The fix: always pick max(line_id) among the candidates. The most recently created
line (highest auto-increment ID) is the correct saved content because every PATCH
creates new ScriptLine objects with higher IDs than the old ones it replaces.

The earlier migration also left orphaned script_lines and script_line_parts rows
in the database. This migration removes them.

Root cause of the corruption it repairs: when a line's line_parts array grew,
deep-object-diff classified the line index as "added". The frontend sent it in
status["added"]. The backend "added" branch created a new
ScriptLineRevisionAssociation without removing the old one, leaving a split
doubly-linked list and a NULL next_line_id at the page boundary.
"""

from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "897ae2963f6d"
down_revision: Union[str, None] = "d2e0b8414d17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _page_walk(conn, revision_id):
    """Walk pages using bridge detection. Returns {page: [line_id, ...]}.

    The first line of page N is identified by:
      - previous_line_id IS NULL  (global head, page 1), or
      - previous_line.page == page - 1  (cross-page pointer)

    When multiple lines on the same page both satisfy this condition (the
    corruption pattern caused by the status["added"] bug), pick max(line_id).
    The highest line_id is the most recently created row and is therefore the
    correct saved content.
    """
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

    by_page = defaultdict(dict)
    for row in rows:
        line_id, next_id, prev_id, page, prev_page = row
        page = page if page is not None else 0
        by_page[page][line_id] = {
            "next": next_id,
            "prev": prev_id,
            "prev_page": prev_page,
        }

    result = {}
    for page in sorted(by_page.keys()):
        page_lines = by_page[page]

        # Collect all candidates for the bridge (first) line of this page.
        candidates = [
            lid
            for lid, d in page_lines.items()
            if d["prev"] is None
            or (d["prev_page"] is not None and d["prev_page"] == page - 1)
        ]

        if not candidates:
            result[page] = []
            continue

        # max(line_id): most recently created = correct saved content.
        first_line_id = max(candidates)

        ordered = []
        current = first_line_id
        seen = set()
        while current is not None and current in page_lines:
            if current in seen:
                break
            seen.add(current)
            ordered.append(current)
            current = page_lines[current]["next"]

        result[page] = ordered

    return result


def _repair_revision(conn, revision_id):
    """Repair linked-list pointers and remove orphans for one revision.

    Returns a summary dict with counts of changes applied.
    """
    page_ordered = _page_walk(conn, revision_id)

    global_order = []
    for page in sorted(page_ordered.keys()):
        global_order.extend(page_ordered[page])

    expected = {}
    for i, line_id in enumerate(global_order):
        expected[line_id] = (
            global_order[i + 1] if i + 1 < len(global_order) else None,
            global_order[i - 1] if i > 0 else None,
        )

    current_rows = conn.execute(
        sa.text(
            "SELECT line_id, next_line_id, previous_line_id "
            "FROM script_line_revision_association WHERE revision_id = :rev_id"
        ),
        {"rev_id": revision_id},
    ).fetchall()
    current_by_id = {row[0]: (row[1], row[2]) for row in current_rows}

    updates = []
    for line_id, (exp_next, exp_prev) in expected.items():
        curr_next, curr_prev = current_by_id.get(line_id, (None, None))
        if curr_next != exp_next or curr_prev != exp_prev:
            updates.append((exp_next, exp_prev, revision_id, line_id))

    reachable_set = set(global_order)
    orphan_ids = set(current_by_id.keys()) - reachable_set

    if orphan_ids:
        # Delete cue associations for orphaned lines first (FK ordering)
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

    if updates:
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

    # Remove orphaned script_line_parts and script_lines rows.
    # A script_line is orphaned when it has no revision associations at all.
    # Delete parts first (FK child), then the line.
    if orphan_ids:
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

    return {
        "revision_id": revision_id,
        "total": len(current_by_id),
        "pointer_updates": len(updates),
        "orphans_deleted": len(orphan_ids),
    }


def upgrade() -> None:
    conn = op.get_bind()
    print("Repairing ScriptLineRevisionAssociation linked lists (max-bridge pass)…")

    revision_ids = [
        row[0]
        for row in conn.execute(
            sa.text("SELECT id FROM script_revisions ORDER BY id")
        ).fetchall()
    ]

    total_updates = 0
    total_orphans = 0
    for rev_id in revision_ids:
        result = _repair_revision(conn, rev_id)
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


def downgrade() -> None:
    pass  # data repair cannot be reversed
