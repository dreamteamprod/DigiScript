"""Add show_current_cue_footer user setting

Revision ID: e96bdd11ca42
Revises: f1974e4e57d0
Create Date: 2026-07-09 12:28:26.922816

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e96bdd11ca42"
down_revision: Union[str, None] = "f1974e4e57d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column as nullable first so existing rows can be backfilled
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("show_current_cue_footer", sa.Boolean(), nullable=True)
        )

    # Backfill existing rows to True (feature defaults to on)
    op.execute(
        "UPDATE user_settings SET show_current_cue_footer = 1 "
        "WHERE show_current_cue_footer IS NULL"
    )

    # Make column non-nullable
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.alter_column(
            "show_current_cue_footer", existing_type=sa.Boolean(), nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.drop_column("show_current_cue_footer")
