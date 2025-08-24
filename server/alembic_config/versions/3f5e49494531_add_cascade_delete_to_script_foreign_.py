"""add_cascade_delete_to_script_foreign_keys

Revision ID: 3f5e49494531
Revises: 8c78b9c89ee6
Create Date: 2025-08-24 22:49:25.592155

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3f5e49494531'
down_revision: Union[str, None] = '8c78b9c89ee6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add ON DELETE CASCADE to foreign key constraints for script_lines relationships.
    
    Since SQLite doesn't support modifying foreign key constraints directly,
    we need to recreate the affected tables with the proper constraints.
    """
    # Create the new tables with CASCADE delete constraints
    
    # 1. Recreate script_line_parts with cascade delete
    op.execute("""
        CREATE TABLE script_line_parts_new (
            id INTEGER NOT NULL, 
            line_id INTEGER, 
            part_index INTEGER, 
            character_id INTEGER, 
            character_group_id INTEGER, 
            line_text VARCHAR, 
            CONSTRAINT pk_script_line_parts PRIMARY KEY (id), 
            CONSTRAINT fk_script_line_parts_line_id_script_lines FOREIGN KEY(line_id) REFERENCES script_lines (id) ON DELETE CASCADE, 
            CONSTRAINT fk_script_line_parts_character_id_character FOREIGN KEY(character_id) REFERENCES character (id), 
            CONSTRAINT fk_script_line_parts_character_group_id_character_group FOREIGN KEY(character_group_id) REFERENCES character_group (id)
        )
    """)
    
    # Copy data from old table
    op.execute("""
        INSERT INTO script_line_parts_new (id, line_id, part_index, character_id, character_group_id, line_text)
        SELECT id, line_id, part_index, character_id, character_group_id, line_text
        FROM script_line_parts
    """)
    
    # Drop old table and rename new one
    op.execute("DROP TABLE script_line_parts")
    op.execute("ALTER TABLE script_line_parts_new RENAME TO script_line_parts")
    
    # 2. Recreate script_line_revision_association with cascade delete
    op.execute("""
        CREATE TABLE script_line_revision_association_new (
            revision_id INTEGER NOT NULL, 
            line_id INTEGER NOT NULL, 
            next_line_id INTEGER, 
            previous_line_id INTEGER, 
            CONSTRAINT pk_script_line_revision_association PRIMARY KEY (revision_id, line_id), 
            CONSTRAINT fk_script_line_revision_association_revision_id_script_revisions FOREIGN KEY(revision_id) REFERENCES script_revisions (id), 
            CONSTRAINT fk_script_line_revision_association_line_id_script_lines FOREIGN KEY(line_id) REFERENCES script_lines (id) ON DELETE CASCADE, 
            CONSTRAINT fk_script_line_revision_association_next_line_id_script_lines FOREIGN KEY(next_line_id) REFERENCES script_lines (id) ON DELETE CASCADE, 
            CONSTRAINT fk_script_line_revision_association_previous_line_id_script_lines FOREIGN KEY(previous_line_id) REFERENCES script_lines (id) ON DELETE CASCADE
        )
    """)
    
    # Copy data from old table
    op.execute("""
        INSERT INTO script_line_revision_association_new (revision_id, line_id, next_line_id, previous_line_id)
        SELECT revision_id, line_id, next_line_id, previous_line_id
        FROM script_line_revision_association
    """)
    
    # Drop existing indexes before dropping the old table
    op.execute("DROP INDEX IF EXISTS ix_script_line_revision_association_revision_id")
    op.execute("DROP INDEX IF EXISTS ix_script_line_revision_association_line_id")
    
    # Drop old table and rename new one
    op.execute("DROP TABLE script_line_revision_association")
    op.execute("ALTER TABLE script_line_revision_association_new RENAME TO script_line_revision_association")
    
    # Recreate the indexes on the new table
    op.execute("CREATE INDEX ix_script_line_revision_association_revision_id ON script_line_revision_association (revision_id)")
    op.execute("CREATE INDEX ix_script_line_revision_association_line_id ON script_line_revision_association (line_id)")
    
    # 3. Recreate script_cue_association with cascade delete
    op.execute("""
        CREATE TABLE script_cue_association_new (
            revision_id INTEGER NOT NULL, 
            line_id INTEGER NOT NULL, 
            cue_id INTEGER NOT NULL, 
            CONSTRAINT pk_script_cue_association PRIMARY KEY (revision_id, line_id, cue_id), 
            CONSTRAINT fk_script_cue_association_revision_id_script_revisions FOREIGN KEY(revision_id) REFERENCES script_revisions (id), 
            CONSTRAINT fk_script_cue_association_line_id_script_lines FOREIGN KEY(line_id) REFERENCES script_lines (id) ON DELETE CASCADE, 
            CONSTRAINT fk_script_cue_association_cue_id_cue FOREIGN KEY(cue_id) REFERENCES cue (id)
        )
    """)
    
    # Copy data from old table
    op.execute("""
        INSERT INTO script_cue_association_new (revision_id, line_id, cue_id)
        SELECT revision_id, line_id, cue_id
        FROM script_cue_association
    """)
    
    # Drop old table and rename new one
    op.execute("DROP TABLE script_cue_association")
    op.execute("ALTER TABLE script_cue_association_new RENAME TO script_cue_association")


def downgrade() -> None:
    """
    Remove ON DELETE CASCADE from foreign key constraints for script_lines relationships.
    
    This reverts the changes made in the upgrade() function by recreating the tables
    without the CASCADE delete constraints.
    """
    # 1. Recreate script_line_parts without cascade delete
    op.execute("""
        CREATE TABLE script_line_parts_old (
            id INTEGER NOT NULL, 
            line_id INTEGER, 
            part_index INTEGER, 
            character_id INTEGER, 
            character_group_id INTEGER, 
            line_text VARCHAR, 
            CONSTRAINT pk_script_line_parts PRIMARY KEY (id), 
            CONSTRAINT fk_script_line_parts_line_id_script_lines FOREIGN KEY(line_id) REFERENCES script_lines (id), 
            CONSTRAINT fk_script_line_parts_character_id_character FOREIGN KEY(character_id) REFERENCES character (id), 
            CONSTRAINT fk_script_line_parts_character_group_id_character_group FOREIGN KEY(character_group_id) REFERENCES character_group (id)
        )
    """)
    
    # Copy data from current table
    op.execute("""
        INSERT INTO script_line_parts_old (id, line_id, part_index, character_id, character_group_id, line_text)
        SELECT id, line_id, part_index, character_id, character_group_id, line_text
        FROM script_line_parts
    """)
    
    # Drop current table and rename old one
    op.execute("DROP TABLE script_line_parts")
    op.execute("ALTER TABLE script_line_parts_old RENAME TO script_line_parts")
    
    # 2. Recreate script_line_revision_association without cascade delete
    op.execute("""
        CREATE TABLE script_line_revision_association_old (
            revision_id INTEGER NOT NULL, 
            line_id INTEGER NOT NULL, 
            next_line_id INTEGER, 
            previous_line_id INTEGER, 
            CONSTRAINT pk_script_line_revision_association PRIMARY KEY (revision_id, line_id), 
            CONSTRAINT fk_script_line_revision_association_revision_id_script_revisions FOREIGN KEY(revision_id) REFERENCES script_revisions (id), 
            CONSTRAINT fk_script_line_revision_association_line_id_script_lines FOREIGN KEY(line_id) REFERENCES script_lines (id), 
            CONSTRAINT fk_script_line_revision_association_next_line_id_script_lines FOREIGN KEY(next_line_id) REFERENCES script_lines (id), 
            CONSTRAINT fk_script_line_revision_association_previous_line_id_script_lines FOREIGN KEY(previous_line_id) REFERENCES script_lines (id)
        )
    """)
    
    # Copy data from current table
    op.execute("""
        INSERT INTO script_line_revision_association_old (revision_id, line_id, next_line_id, previous_line_id)
        SELECT revision_id, line_id, next_line_id, previous_line_id
        FROM script_line_revision_association
    """)
    
    # Create indexes on the old table
    op.execute("CREATE INDEX ix_script_line_revision_association_revision_id ON script_line_revision_association_old (revision_id)")
    op.execute("CREATE INDEX ix_script_line_revision_association_line_id ON script_line_revision_association_old (line_id)")
    
    # Drop current table and rename old one
    op.execute("DROP TABLE script_line_revision_association")
    op.execute("ALTER TABLE script_line_revision_association_old RENAME TO script_line_revision_association")
    
    # 3. Recreate script_cue_association without cascade delete
    op.execute("""
        CREATE TABLE script_cue_association_old (
            revision_id INTEGER NOT NULL, 
            line_id INTEGER NOT NULL, 
            cue_id INTEGER NOT NULL, 
            CONSTRAINT pk_script_cue_association PRIMARY KEY (revision_id, line_id, cue_id), 
            CONSTRAINT fk_script_cue_association_revision_id_script_revisions FOREIGN KEY(revision_id) REFERENCES script_revisions (id), 
            CONSTRAINT fk_script_cue_association_line_id_script_lines FOREIGN KEY(line_id) REFERENCES script_lines (id), 
            CONSTRAINT fk_script_cue_association_cue_id_cue FOREIGN KEY(cue_id) REFERENCES cue (id)
        )
    """)
    
    # Copy data from current table
    op.execute("""
        INSERT INTO script_cue_association_old (revision_id, line_id, cue_id)
        SELECT revision_id, line_id, cue_id
        FROM script_cue_association
    """)
    
    # Drop current table and rename old one
    op.execute("DROP TABLE script_cue_association")
    op.execute("ALTER TABLE script_cue_association_old RENAME TO script_cue_association")
