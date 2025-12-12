"""cleanup_orphaned_script_objects

Revision ID: 42d0eaa5d07e
Revises: e1a2b3c4d5e6
Create Date: 2025-12-12 09:54:39.096643

This migration cleans up orphaned script objects that were left behind due to
bug #768. Orphaned objects include:
- ScriptLine objects with no FK references
- ScriptLinePart objects (cascade deleted with ScriptLine)
- ScriptCuts objects (cascade deleted with ScriptLinePart)
- Cue objects with no FK references

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "42d0eaa5d07e"
down_revision: Union[str, None] = "e1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get database connection
    conn = op.get_bind()

    # 1. Find and delete orphaned Cue objects
    # Cues are orphaned if they have no references in script_cue_association
    orphaned_cues = conn.execute(
        sa.text("""
        SELECT c.id
        FROM cue c
        LEFT JOIN script_cue_association sca ON c.id = sca.cue_id
        WHERE sca.cue_id IS NULL
    """)
    ).fetchall()

    if orphaned_cues:
        orphaned_cue_ids = [row[0] for row in orphaned_cues]
        print(f"Found {len(orphaned_cue_ids)} orphaned cue(s): {orphaned_cue_ids}")
        for cue_id in orphaned_cue_ids:
            conn.execute(sa.text("DELETE FROM cue WHERE id = :id"), {"id": cue_id})

    # 2. Find and delete orphaned ScriptLine objects
    # Lines are orphaned if they have no references in:
    # - script_line_revision_association.line_id
    # - script_line_revision_association.next_line_id
    # - script_line_revision_association.previous_line_id
    # - script_cue_association.line_id
    orphaned_lines = conn.execute(
        sa.text("""
        SELECT sl.id
        FROM script_lines sl
        LEFT JOIN script_line_revision_association slra_line ON sl.id = slra_line.line_id
        LEFT JOIN script_line_revision_association slra_next ON sl.id = slra_next.next_line_id
        LEFT JOIN script_line_revision_association slra_prev ON sl.id = slra_prev.previous_line_id
        LEFT JOIN script_cue_association sca ON sl.id = sca.line_id
        WHERE slra_line.line_id IS NULL
          AND slra_next.next_line_id IS NULL
          AND slra_prev.previous_line_id IS NULL
          AND sca.line_id IS NULL
    """)
    ).fetchall()

    if orphaned_lines:
        orphaned_line_ids = [row[0] for row in orphaned_lines]
        print(
            f"Found {len(orphaned_line_ids)} orphaned script_line(s): {orphaned_line_ids}"
        )
        # ScriptLinePart and ScriptCuts will cascade delete via SQLAlchemy relationships
        for line_id in orphaned_line_ids:
            conn.execute(
                sa.text("DELETE FROM script_lines WHERE id = :id"), {"id": line_id}
            )


def downgrade() -> None:
    # This migration only deletes orphaned data, so there's no meaningful downgrade
    # The orphaned data is already gone from the database by definition
    pass
