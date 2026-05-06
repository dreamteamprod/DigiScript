"""fix_duplicate_sessions_user_id_fk

Migration 29471f7cf7d2 added the named FK fk_sessions_user_id_user to the
sessions table but did not drop the pre-existing unnamed FK on the same column.
Databases upgraded through that migration therefore ended up with two FK
constraints on sessions.user_id, which causes SQLAlchemy to emit a SAWarning
during every subsequent migration run.

This migration drops the unnamed duplicate, leaving only the named constraint
with ON DELETE SET NULL.  The try/except mirrors the pattern in a4d42ccfb71a:
databases that were created from scratch (never had the unnamed FK) would raise
IndexError from drop_constraint(None), which we safely ignore.

Revision ID: d2e0b8414d17
Revises: d3e9f0c1a2b4
Create Date: 2026-05-06 19:13:55.162159

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d2e0b8414d17"
down_revision: Union[str, None] = "d3e9f0c1a2b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The unnamed duplicate FK is invisible to SQLAlchemy reflection, so
    # drop_constraint(None) finds nothing.  Instead, drop and recreate the
    # named constraint: this forces SQLite batch mode to rebuild the table
    # from the reflected schema (which only sees the named FK), so the
    # unnamed duplicate is silently excluded from the new table.
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.drop_constraint(
            batch_op.f("fk_sessions_user_id_user"), type_="foreignkey"
        )
        batch_op.create_foreign_key(
            batch_op.f("fk_sessions_user_id_user"),
            "user",
            ["user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    # Restore the unnamed FK (pre-29471f7cf7d2 state) alongside the named one.
    with op.batch_alter_table("sessions", schema=None) as batch_op:
        batch_op.create_foreign_key(None, "user", ["user_id"], ["id"])
