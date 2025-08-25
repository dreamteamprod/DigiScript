#!/usr/bin/env python3
"""
Test script to reproduce the exact issue from the log files for issue #670.

This test recreates the real-world scenario where users attempted to edit/delete
script lines and received "FOREIGN KEY constraint failed" errors.

Based on log analysis:
- Multiple PATCH /api/v1/show/script?page=1 requests failed
- All failures were attempting: DELETE FROM script_lines WHERE script_lines.id = 1
- The script_line with ID=1 had dependent records preventing deletion
"""

import unittest

from models import models
from models.cue import Cue, CueAssociation, CueType
from models.script import (
    Script,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptRevision,
)
from models.show import Act, Character, Scene, Show

from .test_utils import DigiScriptTestCase


class TestIssue670Reproduction(DigiScriptTestCase):
    """Test that reproduces the exact issue #670 scenario from log files."""

    def setUp(self):
        """Set up the exact scenario that caused the issue in production."""
        super().setUp()

        # Apply our cascade delete migration to the test database
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

        cursor.execute("DROP TABLE script_line_revision_association")
        cursor.execute(
            "ALTER TABLE script_line_revision_association_new RENAME TO script_line_revision_association"
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

    def test_reproduce_script_line_deletion_issue(self):
        """Test that reproduces the exact scenario from the log files."""

        # Create the exact data structure that existed in production
        with models.db.sessionmaker() as session:
            # Create show and related entities (from log analysis)
            show = Show(name="Production Show")
            session.add(show)
            session.flush()

            # Create act and scene
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()

            # Create characters (IDs from logs: 19, 18, 13, 1)
            characters = []
            for char_id in [1, 13, 18, 19]:
                char = Character(show_id=show.id, name=f"Character {char_id}")
                session.add(char)
                characters.append(char)
            session.flush()

            # Create script and revision
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Production revision"
            )
            session.add(revision)
            session.flush()

            # Create script lines with exact data from logs
            line1 = ScriptLine(
                act_id=act.id, scene_id=scene.id, page=1, stage_direction=False
            )
            line2 = ScriptLine(
                act_id=act.id, scene_id=scene.id, page=1, stage_direction=True
            )
            session.add_all([line1, line2])
            session.flush()

            # Create line parts with exact data from logs
            # From logs: {'id': 1, 'line_id': 1, 'part_index': 0, 'character_id': 19, 'line_text': '"Onder leiding van Chiel van Tok"'}
            part1 = ScriptLinePart(
                line_id=line1.id,
                part_index=0,
                character_id=characters[3].id,  # character 19
                line_text='"Onder leiding van Chiel van Tok"',
            )
            # From logs: {'id': 2, 'line_id': 2, 'part_index': 0, 'line_text': 'Ouverture'}
            part2 = ScriptLinePart(
                line_id=line2.id,
                part_index=0,
                character_id=None,
                line_text="Ouverture",
            )
            session.add_all([part1, part2])
            session.flush()

            # Create revision associations (the exact relationships that caused the issue)
            assoc1 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line1.id, next_line_id=line2.id
            )
            assoc2 = ScriptLineRevisionAssociation(
                revision_id=revision.id,
                line_id=line2.id,
                previous_line_id=line1.id,
            )
            session.add_all([assoc1, assoc2])
            session.flush()

            # Create cue association (another dependency that caused issues)
            cue_type = CueType(show_id=show.id, prefix="Licht", description="")
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

        # Verify the problematic state exists (dependencies on line 1)
        with models.db.sessionmaker() as session:
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

            self.assertEqual(parts_count, 1, "Should have 1 line part for line 1")
            self.assertEqual(
                rev_assocs_count, 1, "Should have 1 revision association for line 1"
            )
            self.assertEqual(
                cue_assocs_count, 1, "Should have 1 cue association for line 1"
            )

        # NOW TEST: Attempt to delete script line 1 (this would have failed before our fix)
        # This reproduces the exact operation that failed in the logs:
        # [SQL: DELETE FROM script_lines WHERE script_lines.id = ?] [parameters: (1,)]
        with models.db.sessionmaker() as session:
            line_to_delete = session.get(ScriptLine, line1_id)
            self.assertIsNotNone(line_to_delete, "Line 1 should exist")

            # Before our fix, this deletion would fail with:
            # sqlalchemy.exc.IntegrityError: FOREIGN KEY constraint failed
            # After our fix, it should succeed with cascade delete
            session.delete(line_to_delete)

            # This would raise an exception before our fix, but should succeed now
            session.commit()

        # Verify that cascade delete worked correctly
        with models.db.sessionmaker() as session:
            # All dependent records should be automatically deleted
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

            # The line itself should be gone
            deleted_line = session.get(ScriptLine, line1_id)

            # Verify line2 and its dependencies still exist (unaffected)
            line2_exists = session.get(ScriptLine, line2_id) is not None
            line2_parts_count = (
                session.query(ScriptLinePart).filter_by(line_id=line2_id).count()
            )

            # All line1 dependencies should be CASCADE deleted
            self.assertEqual(parts_count, 0, "Line parts should be cascade deleted")
            self.assertEqual(
                rev_assocs_count, 0, "Revision associations should be cascade deleted"
            )
            self.assertEqual(
                cue_assocs_count, 0, "Cue associations should be cascade deleted"
            )
            self.assertEqual(
                next_refs, 0, "Next line references should be cascade deleted"
            )
            self.assertEqual(
                prev_refs, 0, "Previous line references should be cascade deleted"
            )
            self.assertIsNone(deleted_line, "Line 1 should be deleted")

            # Unrelated data should still exist
            self.assertTrue(line2_exists, "Line 2 should still exist")
            self.assertEqual(line2_parts_count, 1, "Line 2 parts should still exist")

    def test_multiple_script_edit_operations(self):
        """Test multiple script edit operations as seen in the logs."""

        # This test simulates the repetitive PATCH operations that failed in logs
        with models.db.sessionmaker() as session:
            # Create minimal test data
            show = Show(name="Test Show")
            session.add(show)
            session.flush()

            act = Act(show_id=show.id, name="Act 1")
            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            character = Character(show_id=show.id, name="Test Character")
            session.add_all([act, scene, character])
            session.flush()

            script = Script(show_id=show.id)
            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test revision"
            )
            session.add_all([script, revision])
            session.flush()

            # Create multiple script lines
            lines = []
            for i in range(3):
                line = ScriptLine(
                    act_id=act.id, scene_id=scene.id, page=1, stage_direction=False
                )
                lines.append(line)
            session.add_all(lines)
            session.flush()

            # Create dependencies for each line
            for i, line in enumerate(lines):
                # Line parts
                part = ScriptLinePart(
                    line_id=line.id,
                    part_index=0,
                    character_id=character.id,
                    line_text=f"Line {i+1} text",
                )
                session.add(part)

                # Revision associations
                assoc = ScriptLineRevisionAssociation(
                    revision_id=revision.id, line_id=line.id
                )
                session.add(assoc)

            session.commit()

        # Test: Delete lines one by one (simulating user edit operations)
        with models.db.sessionmaker() as session:
            lines_to_delete = session.query(ScriptLine).all()
            line_ids = [line.id for line in lines_to_delete]

            # Before our fix, any of these deletions would fail
            # After our fix, they should all succeed due to cascade delete
            for line in lines_to_delete:
                session.delete(line)
                session.commit()  # Commit each deletion separately

        # Verify all dependencies were properly cascade deleted
        with models.db.sessionmaker() as session:
            for line_id in line_ids:
                parts_count = (
                    session.query(ScriptLinePart).filter_by(line_id=line_id).count()
                )
                rev_assocs_count = (
                    session.query(ScriptLineRevisionAssociation)
                    .filter_by(line_id=line_id)
                    .count()
                )

                self.assertEqual(
                    parts_count, 0, f"Parts for line {line_id} should be deleted"
                )
                self.assertEqual(
                    rev_assocs_count,
                    0,
                    f"Revision associations for line {line_id} should be deleted",
                )

                # The line itself should be gone
                deleted_line = session.get(ScriptLine, line_id)
                self.assertIsNone(deleted_line, f"Line {line_id} should be deleted")


if __name__ == "__main__":
    unittest.main()
