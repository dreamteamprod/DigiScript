"""empty message

Revision ID: 14f82e306537
Revises: 43fcd5292e0f, c1db8c1f4e37
Create Date: 2026-02-21 01:03:49.886807

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "14f82e306537"
down_revision: Union[str, None] = ("43fcd5292e0f", "c1db8c1f4e37")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
