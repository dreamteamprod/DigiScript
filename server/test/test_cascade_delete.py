#!/usr/bin/env python3
"""
Test script to verify that the cascade delete migration works correctly.

This test creates sample data and verifies that deleting a script_line
properly cascades to delete dependent records in:
- script_line_parts
- script_line_revision_association
- script_cue_association

This addresses the SQLAlchemy IntegrityError: FOREIGN KEY constraint failed
"""

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from models import models
from models.cue import Cue, CueAssociation, CueType
from models.models import db
from models.script import (
    Script,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptRevision,
)
from models.show import Act, Character, Scene, Show

from .test_utils import DigiScriptTestCase


class TestCascadeDelete(DigiScriptTestCase):
    """Test cascade delete functionality after migration."""

    def setUp(self):
        """Set up test database with cascade delete constraints."""
        super().setUp()

        # Apply the cascade delete migration manually to test database
        # Get the database connection from the app
        conn = self._app.get_db().engine.raw_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")

        # Apply migration for script_line_parts
        cursor.execute(
            """
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
        """
        )

        cursor.execute(
            """
            INSERT INTO script_line_parts_new (id, line_id, part_index, character_id, character_group_id, line_text)
            SELECT id, line_id, part_index, character_id, character_group_id, line_text
            FROM script_line_parts
        """
        )

        cursor.execute("DROP TABLE script_line_parts")
        cursor.execute("ALTER TABLE script_line_parts_new RENAME TO script_line_parts")

        # Apply migration for script_line_revision_association
        cursor.execute(
            """
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
        """
        )

        cursor.execute(
            """
            INSERT INTO script_line_revision_association_new (revision_id, line_id, next_line_id, previous_line_id)
            SELECT revision_id, line_id, next_line_id, previous_line_id
            FROM script_line_revision_association
        """
        )

        cursor.execute(
            "DROP INDEX IF EXISTS ix_script_line_revision_association_revision_id"
        )
        cursor.execute(
            "DROP INDEX IF EXISTS ix_script_line_revision_association_line_id"
        )
        cursor.execute("DROP TABLE script_line_revision_association")
        cursor.execute(
            "ALTER TABLE script_line_revision_association_new RENAME TO script_line_revision_association"
        )
        cursor.execute(
            "CREATE INDEX ix_script_line_revision_association_revision_id ON script_line_revision_association (revision_id)"
        )
        cursor.execute(
            "CREATE INDEX ix_script_line_revision_association_line_id ON script_line_revision_association (line_id)"
        )

        # Apply migration for script_cue_association
        cursor.execute(
            """
            CREATE TABLE script_cue_association_new (
                revision_id INTEGER NOT NULL, 
                line_id INTEGER NOT NULL, 
                cue_id INTEGER NOT NULL, 
                CONSTRAINT pk_script_cue_association PRIMARY KEY (revision_id, line_id, cue_id), 
                CONSTRAINT fk_script_cue_association_revision_id_script_revisions FOREIGN KEY(revision_id) REFERENCES script_revisions (id), 
                CONSTRAINT fk_script_cue_association_line_id_script_lines FOREIGN KEY(line_id) REFERENCES script_lines (id) ON DELETE CASCADE, 
                CONSTRAINT fk_script_cue_association_cue_id_cue FOREIGN KEY(cue_id) REFERENCES cue (id)
            )
        """
        )

        cursor.execute(
            """
            INSERT INTO script_cue_association_new (revision_id, line_id, cue_id)
            SELECT revision_id, line_id, cue_id
            FROM script_cue_association
        """
        )

        cursor.execute("DROP TABLE script_cue_association")
        cursor.execute(
            "ALTER TABLE script_cue_association_new RENAME TO script_cue_association"
        )

        conn.commit()
        conn.close()

    def test_cascade_delete_script_line(self):
        """Test that deleting a script line cascades to delete dependent records."""

        # Create test data
        with db.sessionmaker() as session:
            # Create a show and related entities
            show = Show(name="Test Show")
            session.add(show)
            session.flush()

            # Create act and scene
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()

            # Create character
            character = Character(show_id=show.id, name="Test Character")
            session.add(character)
            session.flush()

            # Create script and revision
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test revision"
            )
            session.add(revision)
            session.flush()

            # Create script lines
            line1 = ScriptLine(
                act_id=act.id, scene_id=scene.id, page=1, stage_direction=False
            )
            line2 = ScriptLine(
                act_id=act.id, scene_id=scene.id, page=1, stage_direction=False
            )
            session.add_all([line1, line2])
            session.flush()

            # Create script line parts
            part1 = ScriptLinePart(
                line_id=line1.id,
                part_index=1,
                character_id=character.id,
                line_text="Hello world!",
            )
            part2 = ScriptLinePart(
                line_id=line1.id,
                part_index=2,
                character_id=character.id,
                line_text="This is a test.",
            )
            session.add_all([part1, part2])
            session.flush()

            # Create revision associations
            assoc1 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line1.id, next_line_id=line2.id
            )
            assoc2 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line2.id, previous_line_id=line1.id
            )
            session.add_all([assoc1, assoc2])
            session.flush()

            # Create cue and cue association
            cue_type = CueType(show_id=show.id, prefix="LX", description="Lighting")
            session.add(cue_type)
            session.flush()

            cue = Cue(cue_type_id=cue_type.id, ident="1")
            session.add(cue)
            session.flush()

            cue_assoc = CueAssociation(
                revision_id=revision.id, line_id=line1.id, cue_id=cue.id
            )
            session.add(cue_assoc)

            session.commit()

            line1_id = line1.id
            line2_id = line2.id

        # Verify data exists before deletion
        with db.sessionmaker() as session:
            parts_count = (
                session.query(ScriptLinePart).filter_by(line_id=line1_id).count()
            )
            rev_assocs_count = (
                session.query(ScriptLineRevisionAssociation)
                .filter_by(line_id=line1_id)
                .count()
            )
            cue_assocs_count = (
                session.query(CueAssociation).filter_by(line_id=line1_id).count()
            )

            self.assertEqual(parts_count, 2, "Should have 2 line parts before deletion")
            self.assertEqual(
                rev_assocs_count,
                1,
                "Should have 1 revision association before deletion",
            )
            self.assertEqual(
                cue_assocs_count, 1, "Should have 1 cue association before deletion"
            )

        # Test cascade delete by deleting line1
        with db.sessionmaker() as session:
            line_to_delete = session.get(ScriptLine, line1_id)
            self.assertIsNotNone(line_to_delete, "Line should exist before deletion")
            session.delete(line_to_delete)
            session.commit()

        # Verify cascade delete worked
        with db.sessionmaker() as session:
            parts_count = (
                session.query(ScriptLinePart).filter_by(line_id=line1_id).count()
            )
            rev_assocs_count = (
                session.query(ScriptLineRevisionAssociation)
                .filter_by(line_id=line1_id)
                .count()
            )
            cue_assocs_count = (
                session.query(CueAssociation).filter_by(line_id=line1_id).count()
            )

            # Also check references to line1_id in next_line_id and previous_line_id
            next_refs = (
                session.query(ScriptLineRevisionAssociation)
                .filter_by(next_line_id=line1_id)
                .count()
            )
            prev_refs = (
                session.query(ScriptLineRevisionAssociation)
                .filter_by(previous_line_id=line1_id)
                .count()
            )

            # Verify line2 still exists and is unaffected
            line2_exists = session.get(ScriptLine, line2_id) is not None

            # All dependent records should be deleted
            self.assertEqual(parts_count, 0, "All line parts should be deleted")
            self.assertEqual(
                rev_assocs_count, 0, "All revision associations should be deleted"
            )
            self.assertEqual(
                cue_assocs_count, 0, "All cue associations should be deleted"
            )
            self.assertEqual(next_refs, 0, "All next line references should be deleted")
            self.assertEqual(
                prev_refs, 0, "All previous line references should be deleted"
            )

            # Unrelated data should still exist
            self.assertTrue(line2_exists, "Unrelated line should still exist")


if __name__ == "__main__":
    unittest.main()
