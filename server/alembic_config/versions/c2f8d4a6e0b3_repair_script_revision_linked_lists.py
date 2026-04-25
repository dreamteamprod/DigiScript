"""repair_script_revision_linked_lists

Revision ID: c2f8d4a6e0b3
Revises: 14f82e306537
Create Date: 2026-02-25 00:00:00.000000

Repairs broken ScriptLineRevisionAssociation linked list pointers.

For each revision, walks pages using bridge detection (same logic as the
GET /api/v1/show/script?page=N endpoint):
  - Bridge line of page N = the line whose previous_line_id points to a
    line on page N-1 (looked up from script_lines directly, not from the
    revision associations — the previous line may have been removed from
    this revision while still existing in script_lines).
  - Walks next_line_id within each page to build page-local order.

Rebuilds next_line_id / previous_line_id for all pointer mismatches.
Deletes true orphans (lines not reachable by any page-local walk).

FK constraints are added in the subsequent migration
(d3e9f0c1a2b4_add_script_revision_fk_constraints.py), which must run
against clean data — that is why the repair is committed first.
"""

from collections import defaultdict
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c2f8d4a6e0b3"
down_revision: Union[str, None] = "14f82e306537"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers: page walk + repair logic (mirrors diagnose_linked_list.py)
# ---------------------------------------------------------------------------


def _page_walk(conn, revision_id):
    """Walk pages using bridge detection. Returns {page: [line_id, ...]}.

    Bridge detection: the first line of page N is the line whose
    previous_line_id points to a line on page N-1 (read directly from
    script_lines, not from the association — the previous line may have been
    removed from this revision while still existing in script_lines).
    """
    rows = conn.execute(
        sa.text(
            """
            SELECT a.line_id, a.next_line_id, a.previous_line_id,
                   l.page AS line_page,
                   lp.page AS prev_page
            FROM script_line_revision_association a
            JOIN script_lines l ON l.id = a.line_id
            LEFT JOIN script_lines lp ON lp.id = a.previous_line_id
            WHERE a.revision_id = :rev_id
            """
        ),
        {"rev_id": revision_id},
    ).fetchall()

    # Group associations by page
    by_page = defaultdict(dict)
    for row in rows:
        line_id = row[0]
        next_line_id = row[1]
        prev_line_id = row[2]
        page = row[3] if row[3] is not None else 0
        prev_page = row[4]

        by_page[page][line_id] = {
            "next": next_line_id,
            "prev": prev_line_id,
            "prev_page": prev_page,
        }

    result = {}

    for page in sorted(by_page.keys()):
        page_lines = by_page[page]

        # Find the bridge line (first line on this page):
        #   - previous_line_id IS NULL  (global head), or
        #   - previous_line.page == page - 1  (cross-page pointer)
        first_line_id = None
        for line_id, d in page_lines.items():
            prev_id = d["prev"]
            prev_page = d["prev_page"]
            if prev_id is None or (prev_page is not None and prev_page == page - 1):
                first_line_id = line_id
                break

        if first_line_id is None:
            result[page] = []
            continue

        # Walk within this page following next_line_id
        ordered = []
        current = first_line_id
        seen = set()
        while current is not None and current in page_lines:
            if current in seen:
                break  # loop guard
            seen.add(current)
            ordered.append(current)
            current = page_lines[current]["next"]

        result[page] = ordered

    return result


def _repair_revision(conn, revision_id):
    """Repair linked list pointers for one revision.

    Returns a summary dict with counts of changes applied.
    """
    page_ordered = _page_walk(conn, revision_id)

    # Build global order from sorted pages
    global_order = []
    for page in sorted(page_ordered.keys()):
        global_order.extend(page_ordered[page])

    # Compute expected pointers for every line in the repaired chain
    expected = {}
    for i, line_id in enumerate(global_order):
        expected[line_id] = (
            global_order[i + 1] if i + 1 < len(global_order) else None,  # next
            global_order[i - 1] if i > 0 else None,  # prev
        )

    # Fetch current state from DB
    current_rows = conn.execute(
        sa.text(
            "SELECT line_id, next_line_id, previous_line_id "
            "FROM script_line_revision_association WHERE revision_id = :rev_id"
        ),
        {"rev_id": revision_id},
    ).fetchall()
    current_by_id = {row[0]: (row[1], row[2]) for row in current_rows}

    # Lines that need pointer correction
    updates = []  # (new_next, new_prev, revision_id, line_id)
    for line_id, (exp_next, exp_prev) in expected.items():
        curr_next, curr_prev = current_by_id.get(line_id, (None, None))
        if curr_next != exp_next or curr_prev != exp_prev:
            updates.append((exp_next, exp_prev, revision_id, line_id))

    # True orphans: in the revision but not reached by any page-local walk
    reachable_set = set(global_order)
    orphan_ids = set(current_by_id.keys()) - reachable_set

    if orphan_ids:
        print(
            f"  Revision {revision_id}: deleting {len(orphan_ids)} orphan(s): "
            f"{sorted(orphan_ids)}"
        )
        # Delete cue associations for orphaned lines first (FK ordering)
        for orphan_id in orphan_ids:
            conn.execute(
                sa.text(
                    "DELETE FROM script_cue_association "
                    "WHERE revision_id = :rev_id AND line_id = :line_id"
                ),
                {"rev_id": revision_id, "line_id": orphan_id},
            )
        # Delete the orphaned associations themselves
        for orphan_id in orphan_ids:
            conn.execute(
                sa.text(
                    "DELETE FROM script_line_revision_association "
                    "WHERE revision_id = :rev_id AND line_id = :line_id"
                ),
                {"rev_id": revision_id, "line_id": orphan_id},
            )

    if updates:
        print(
            f"  Revision {revision_id}: fixing {len(updates)} pointer(s) "
            f"(out of {len(current_by_id)} associations)"
        )
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

    return {
        "revision_id": revision_id,
        "total": len(current_by_id),
        "pointer_updates": len(updates),
        "orphans_deleted": len(orphan_ids),
    }


# ---------------------------------------------------------------------------
# Migration
# ---------------------------------------------------------------------------


def upgrade() -> None:
    conn = op.get_bind()
    print("Repairing ScriptLineRevisionAssociation linked lists…")

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
        total_updates += result["pointer_updates"]
        total_orphans += result["orphans_deleted"]

    print(
        f"Repair complete: {total_updates} pointer fix(es), "
        f"{total_orphans} orphan(s) deleted across {len(revision_ids)} revision(s)."
    )


def downgrade() -> None:
    pass  # data repair cannot be reversed
