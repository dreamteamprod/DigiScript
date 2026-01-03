"""replace stage_direction with line_type enum

Revision ID: 9f76c42e225e
Revises: f365c2b2b234
Create Date: 2026-01-01 13:24:08.049092

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f76c42e225e"
down_revision: Union[str, None] = "f365c2b2b234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Add line_type column as nullable
    with op.batch_alter_table("script_lines", schema=None) as batch_op:
        batch_op.add_column(sa.Column("line_type", sa.Integer(), nullable=True))

    # Step 2: Migrate data
    # stage_direction=True (1) → line_type=2 (STAGE_DIRECTION)
    # stage_direction=False (0) or NULL → line_type=1 (DIALOGUE)
    op.execute("""
        UPDATE script_lines
        SET line_type = CASE
            WHEN stage_direction = 1 THEN 2
            ELSE 1
        END
    """)

    # Step 3: Make line_type NOT NULL with default value
    with op.batch_alter_table("script_lines", schema=None) as batch_op:
        batch_op.alter_column("line_type", nullable=False, server_default="1")

    # Step 4: Drop old stage_direction column
    with op.batch_alter_table("script_lines", schema=None) as batch_op:
        batch_op.drop_column("stage_direction")


def downgrade() -> None:
    # Step 1: Add back stage_direction column
    with op.batch_alter_table("script_lines", schema=None) as batch_op:
        batch_op.add_column(sa.Column("stage_direction", sa.Boolean(), nullable=True))

    # Step 2: Migrate data back
    # line_type=2 (STAGE_DIRECTION) → stage_direction=True
    # line_type=1,3,4 → stage_direction=False
    op.execute("""
        UPDATE script_lines
        SET stage_direction = CASE
            WHEN line_type = 2 THEN 1
            ELSE 0
        END
    """)

    # Step 3: Drop line_type column
    with op.batch_alter_table("script_lines", schema=None) as batch_op:
        batch_op.drop_column("line_type")
