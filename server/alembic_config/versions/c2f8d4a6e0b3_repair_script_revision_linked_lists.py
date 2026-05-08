"""repair_script_revision_linked_lists

Revision ID: c2f8d4a6e0b3
Revises: c1db8c1f4e37
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

from typing import Sequence, Union

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
revision: str = "c2f8d4a6e0b3"
down_revision: Union[str, None] = "c1db8c1f4e37"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _page_walk(conn, revision_id):
    """Walk pages using bridge detection (first-found bridge selection).

    :note: When multiple lines satisfy the bridge condition, this picks the
        first one in dict-iteration order (non-deterministic). This is the
        original behaviour; migration 897ae2963f6d supersedes it with a
        deterministic ``max(line_id)`` selection.
    """
    by_page = fetch_page_associations(conn, revision_id)
    return build_page_ordered(by_page, lambda candidates: candidates[0])


def _repair_revision(conn, revision_id):
    """Repair linked list pointers for one revision.

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
        print(
            f"  Revision {revision_id}: deleting {len(orphan_ids)} orphan(s): "
            f"{sorted(orphan_ids)}"
        )
        delete_orphan_associations(conn, revision_id, orphan_ids)

    if updates:
        print(
            f"  Revision {revision_id}: fixing {len(updates)} pointer(s) "
            f"(out of {len(current_by_id)} associations)"
        )
        apply_pointer_updates(conn, updates)

    return {
        "revision_id": revision_id,
        "total": len(current_by_id),
        "pointer_updates": len(updates),
        "orphans_deleted": len(orphan_ids),
    }


def upgrade() -> None:
    conn = op.get_bind()
    print("Repairing ScriptLineRevisionAssociation linked lists…")
    revision_ids = fetch_all_revision_ids(conn)
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
