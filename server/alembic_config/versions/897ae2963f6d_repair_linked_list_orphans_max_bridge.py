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

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from alembic_config.repair_linked_list_utils import (
    apply_pointer_updates,
    build_global_order,
    build_page_ordered,
    collect_pointer_updates,
    compute_expected_pointers,
    delete_orphan_associations,
    fetch_all_revision_ids,
    fetch_current_pointers,
    fetch_page_associations,
)


# revision identifiers, used by Alembic.
revision: str = "897ae2963f6d"
down_revision: Union[str, None] = "d2e0b8414d17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _page_walk(conn, revision_id):
    """Walk pages using bridge detection. Returns {page: [line_id, ...]}.

    When multiple lines on the same page both satisfy the bridge condition
    (the corruption pattern caused by the status["added"] bug), pick
    max(line_id). The highest line_id is the most recently created row and
    is therefore the correct saved content.
    """
    by_page = fetch_page_associations(conn, revision_id)
    return build_page_ordered(by_page, max)


def _repair_revision(conn, revision_id):
    """Repair linked-list pointers and remove orphans for one revision.

    :returns: Summary dict with counts of changes applied.
    """
    page_ordered = _page_walk(conn, revision_id)
    global_order = build_global_order(page_ordered)
    expected = compute_expected_pointers(global_order)
    current_by_id = fetch_current_pointers(conn, revision_id)
    updates = collect_pointer_updates(expected, current_by_id, revision_id)
    reachable_set = set(global_order)
    orphan_ids = set(current_by_id.keys()) - reachable_set

    if orphan_ids:
        delete_orphan_associations(conn, revision_id, orphan_ids)
    if updates:
        apply_pointer_updates(conn, updates)

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
    revision_ids = fetch_all_revision_ids(conn)
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
