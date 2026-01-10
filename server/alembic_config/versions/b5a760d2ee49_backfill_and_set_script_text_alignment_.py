"""backfill_and_set_script_text_alignment_not_null

Revision ID: b5a760d2ee49
Revises: 859636b5ffbb
Create Date: 2026-01-09 12:02:21.850022

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b5a760d2ee49"
down_revision: Union[str, None] = "859636b5ffbb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Backfill NULL values to 2 (CENTER) for existing users
    op.execute(
        "UPDATE user_settings SET script_text_alignment = 2 WHERE script_text_alignment IS NULL"
    )

    # Make column non-nullable
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.alter_column(
            "script_text_alignment", existing_type=sa.Integer(), nullable=False
        )


def downgrade() -> None:
    # Make column nullable again
    with op.batch_alter_table("user_settings", schema=None) as batch_op:
        batch_op.alter_column(
            "script_text_alignment", existing_type=sa.Integer(), nullable=True
        )
