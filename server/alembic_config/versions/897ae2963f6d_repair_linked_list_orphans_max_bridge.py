"""repair_linked_list_orphans_max_bridge

Revision ID: 897ae2963f6d
Revises: d2e0b8414d17
Create Date: 2026-05-08 20:37:12.115558

Repairs broken ScriptLineRevisionAssociation linked lists and removes orphaned
script_lines / script_line_parts records.

This supersedes the earlier c2f8d4a6e0b3 repair migration by fixing a bug in
bridge-line selection: when multiple associations for the same page both satisfy
the "first-line" condition (i.e. their previous_line is on page N-1), the old
migration picked whichever came first in dict-iteration order (non-deterministic).

The fix: always pick max(line_id) among the candidates. The most recently created
line (highest auto-increment ID) is the correct saved content because every PATCH
creates new ScriptLine objects with higher IDs than the old ones it replaces.

The earlier migration also left orphaned script_lines and script_line_parts rows
in the database. This migration removes them.

Root cause of the corruption it repairs: when a line's line_parts array grew,
deep-object-diff classified the line index as "added". The frontend sent it in
status["added"]. The backend "added" branch created a new
ScriptLineRevisionAssociation without removing the old one, leaving a split
doubly-linked list and a NULL next_line_id at the page boundary.
"""

from typing import Sequence, Union

from alembic import op

from alembic_config.repair_linked_list_utils import run_max_bridge_repair


# revision identifiers, used by Alembic.
revision: str = "897ae2963f6d"
down_revision: Union[str, None] = "d2e0b8414d17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    run_max_bridge_repair(op.get_bind(), "max-bridge pass")


def downgrade() -> None:
    pass  # data repair cannot be reversed
