"""add_character_mru_sort_to_user_settings

Revision ID: c515969c1a51
Revises: 897ae2963f6d
Create Date: 2026-05-12 19:48:43.975135

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c515969c1a51"
down_revision: Union[str, None] = "897ae2963f6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column as nullable first so existing rows can be backfilled
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("character_mru_sort", sa.Boolean(), nullable=True)
        )

    # Backfill existing rows to False
    op.execute(
        "UPDATE user_settings SET character_mru_sort = 0 WHERE character_mru_sort IS NULL"
    )

    # Make column non-nullable
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.alter_column(
            "character_mru_sort", existing_type=sa.Boolean(), nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.drop_column("character_mru_sort")
