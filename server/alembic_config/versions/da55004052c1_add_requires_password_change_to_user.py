"""add_requires_password_change_to_user

Revision ID: da55004052c1
Revises: b5a760d2ee49
Create Date: 2026-01-10 18:21:49.635525

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "da55004052c1"
down_revision: Union[str, None] = "b5a760d2ee49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add column as nullable
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("requires_password_change", sa.Boolean(), nullable=True)
        )

    # Step 2: Backfill with default value (False for all existing users)
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE user SET requires_password_change = 0 WHERE requires_password_change IS NULL"
        )
    )

    # Step 3: Make column non-nullable
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column("requires_password_change", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("requires_password_change")
