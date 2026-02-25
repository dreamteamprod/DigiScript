"""add_script_revision_fk_constraints

Revision ID: d3e9f0c1a2b4
Revises: c2f8d4a6e0b3
Create Date: 2026-02-25 00:00:00.000000

Adds composite self-referential FK constraints to prevent cross-revision
linked list pointer corruption:

  (revision_id, next_line_id)     → (revision_id, line_id)  DEFERRABLE INITIALLY DEFERRED
  (revision_id, previous_line_id) → (revision_id, line_id)  DEFERRABLE INITIALLY DEFERRED

Must run AFTER c2f8d4a6e0b3 (data repair), because Alembic's SQLite batch
mode executes `INSERT INTO _tmp SELECT * FROM original` in autocommit mode.
In autocommit mode, SQLite treats DEFERRABLE INITIALLY DEFERRED as IMMEDIATE
(there is no surrounding transaction to defer to), so the FK check fires
right after the INSERT.  If the data still contained broken pointers, that
INSERT would fail with an IntegrityError.

With the repair committed first, every (revision_id, next_line_id) and
(revision_id, previous_line_id) value already exists as a valid
(revision_id, line_id) pair, so the batch INSERT succeeds immediately.

DEFERRABLE INITIALLY DEFERRED is still the correct semantics for
application-level usage: during revision creation, associations are inserted
one at a time, and SQLAlchemy uses explicit BEGIN/COMMIT transactions, so
deferred checking fires at COMMIT (when all rows are present).
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d3e9f0c1a2b4"
down_revision: Union[str, None] = "c2f8d4a6e0b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    print("Adding composite FK constraints to script_line_revision_association…")

    with op.batch_alter_table("script_line_revision_association") as batch_op:
        batch_op.create_foreign_key(
            "fk_slra_next_same_revision",
            "script_line_revision_association",
            ["revision_id", "next_line_id"],
            ["revision_id", "line_id"],
            deferrable=True,
            initially="DEFERRED",
        )
        batch_op.create_foreign_key(
            "fk_slra_prev_same_revision",
            "script_line_revision_association",
            ["revision_id", "previous_line_id"],
            ["revision_id", "line_id"],
            deferrable=True,
            initially="DEFERRED",
        )

    print("FK constraints added.")


def downgrade() -> None:
    with op.batch_alter_table("script_line_revision_association") as batch_op:
        batch_op.drop_constraint("fk_slra_next_same_revision", type_="foreignkey")
        batch_op.drop_constraint("fk_slra_prev_same_revision", type_="foreignkey")