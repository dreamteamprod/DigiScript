"""add_token_version_to_user

Revision ID: 01fb1d6c6b08
Revises: da55004052c1
Create Date: 2026-01-11 01:10:17.249232

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "01fb1d6c6b08"
down_revision: Union[str, None] = "da55004052c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add column as nullable
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(sa.Column("token_version", sa.Integer(), nullable=True))

    # Step 2: Backfill with default value (0 for all existing users)
    connection = op.get_bind()
    connection.execute(
        sa.text("UPDATE user SET token_version = 0 WHERE token_version IS NULL")
    )

    # Step 3: Make column non-nullable
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.alter_column("token_version", nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("token_version")
