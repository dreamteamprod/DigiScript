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

from typing import Sequence

from alembic import op

from alembic_config.repair_linked_list_utils import run_max_bridge_repair


# revision identifiers, used by Alembic.
revision: str = "f341c640b571"
down_revision: str | None = "079ddf32e0c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    run_max_bridge_repair(op.get_bind(), "non-last-page-append pass")


def downgrade() -> None:
    pass  # data repair cannot be reversed
