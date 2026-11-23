"""repair_linked_list_non_last_page_append

Revision ID: f341c640b571
Revises: 079ddf32e0c3
Create Date: 2026-11-23 13:08:57.019254

Repairs broken ScriptLineRevisionAssociation linked lists caused by a third,
distinct corruption vector from the ones 897ae2963f6d already repairs.

Root cause: ``create_new_line`` (``utils/script/line_helpers.py``) spliced a
new line in after ``previous_line`` by overwriting ``previous_line.next_line``
without preserving whatever it previously pointed at. Appending a blank line
to the end of a page that is *not* the script's last page (the classic
editor's "add line" button, ``addBlankLine`` in ``scriptConfig.ts`` — and,
since the collaborative save path added in September 2026 shares the same
helper, its equivalent "add line" action too) is exactly this case: the line
being appended to already has a real ``next_line`` — the first line of the
following page — and that link was silently dropped. The classic per-page GET
endpoint never notices, because it only needs each page's own local ordering;
only a consumer that walks the whole document as one chain (collaborative
mode's Y.Doc builder) is affected, as an editor permanently stuck just past
the break.

Unlike the ``added``-vs-``updated`` misclassification 897ae2963f6d repairs,
this one leaves every row with a *page* that is still correct — only the
``next_line_id`` / ``previous_line_id`` pointers past the break are wrong — so
this migration reuses the exact same page-local "bridge" reconstruction
(independent of the broken global chain) rather than needing a new algorithm.
It is safe to run whether or not a revision was ever affected: pages that are
already correctly linked produce zero pointer updates and zero orphans.
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
revision: str = "f341c640b571"
down_revision: Union[str, None] = "079ddf32e0c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _repair_revision(conn, revision_id):
    """Repair linked-list pointers for one revision.

    Reuses the max-bridge page walk from 897ae2963f6d: when several
    associations on a page satisfy the "first line of this page" condition,
    the highest line_id is the correct one, since every replace creates a
    ScriptLine with a higher id than the one it replaces.

    :returns: Summary dict with counts of changes applied.
    """
    page_ordered = build_page_ordered(fetch_page_associations(conn, revision_id), max)
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

    return {
        "revision_id": revision_id,
        "total": len(current_by_id),
        "pointer_updates": len(updates),
        "orphans_deleted": len(orphan_ids),
    }


def upgrade() -> None:
    conn = op.get_bind()
    print(
        "Repairing ScriptLineRevisionAssociation linked lists (non-last-page-append pass)…"
    )
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
