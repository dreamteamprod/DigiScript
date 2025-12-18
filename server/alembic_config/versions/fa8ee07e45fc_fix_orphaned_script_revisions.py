"""fix_orphaned_script_revisions

Revision ID: fa8ee07e45fc
Revises: 42d0eaa5d07e
Create Date: 2025-12-18 22:55:57.281038

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "fa8ee07e45fc"
down_revision: Union[str, None] = "42d0eaa5d07e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix orphaned script revisions by linking them to the initial revision."""
    conn = op.get_bind()

    # Find all orphaned revisions (NULL previous_revision_id and NOT revision 1)
    orphaned_revisions = conn.execute(
        sa.text("""
            SELECT id, script_id, revision
            FROM script_revisions
            WHERE previous_revision_id IS NULL
            AND revision != 1
        """)
    ).fetchall()

    # For each orphaned revision, find the initial revision (revision 1) for that script
    for orphaned in orphaned_revisions:
        orphaned_id, script_id, revision_number = orphaned

        # Find the initial revision (revision = 1) for this script
        initial_revision = conn.execute(
            sa.text("""
                SELECT id
                FROM script_revisions
                WHERE script_id = :script_id
                AND revision = 1
                LIMIT 1
            """),
            {"script_id": script_id},
        ).fetchone()

        if initial_revision:
            # Update the orphaned revision to point to the initial revision
            conn.execute(
                sa.text("""
                    UPDATE script_revisions
                    SET previous_revision_id = :initial_id
                    WHERE id = :orphaned_id
                """),
                {"initial_id": initial_revision[0], "orphaned_id": orphaned_id},
            )
            print(
                f"Fixed orphaned revision {revision_number} (id: {orphaned_id}) "
                f"for script {script_id}, linked to initial revision (id: {initial_revision[0]})"
            )
        else:
            print(
                f"WARNING: Could not find initial revision for script {script_id}, "
                f"orphaned revision {revision_number} (id: {orphaned_id}) remains unfixed"
            )


def downgrade() -> None:
    """
    Downgrade is not implemented for this data migration.

    This migration fixes data integrity by linking orphaned revisions to their
    script's initial revision. There is no meaningful way to reverse this
    operation as we don't track which revisions were originally orphaned.
    """
    pass
