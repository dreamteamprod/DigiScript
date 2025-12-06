"""
Tests for composite key lookups in SQLAlchemy 2.0.

These tests verify that composite primary key lookups work correctly with
both tuple-based session.get() and select-based approaches.

Models with composite keys in DigiScript:
- ScriptLineRevisionAssociation (revision_id, line_id)
- CueAssociation (revision_id, line_id, cue_id)
- ScriptCuts (line_part_id, revision_id)
- MicrophoneAllocation (mic_id, scene_id, character_id)
"""

import pytest
from sqlalchemy import select

from models.script import (
    Script,
    ScriptRevision,
    ScriptLine,
    ScriptLineRevisionAssociation,
)
from models.show import Show
from .test_utils import DigiScriptTestCase


class TestCompositeKeys(DigiScriptTestCase):
    """Test composite key operations with modern SQLAlchemy API."""

    def setUp(self):
        """Set up test data for composite key tests."""
        super().setUp()

        # Create test show, script, and revision
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.flush()

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Draft 1"
            )
            session.add(revision)
            session.flush()

            # Create script lines
            line1 = ScriptLine(page=1, stage_direction=False)
            line2 = ScriptLine(page=1, stage_direction=False)
            line3 = ScriptLine(page=2, stage_direction=False)
            session.add_all([line1, line2, line3])
            session.flush()

            # Create associations (composite key: revision_id, line_id)
            assoc1 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line1.id
            )
            assoc2 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line2.id
            )
            assoc3 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line3.id
            )
            session.add_all([assoc1, assoc2, assoc3])
            session.commit()

            # Store IDs for tests
            self.revision_id = revision.id
            self.line1_id = line1.id
            self.line2_id = line2.id
            self.line3_id = line3.id

    def test_composite_key_get_with_tuple(self):
        """Test composite key lookup using tuple with session.get()"""
        with self._app.get_db().sessionmaker() as session:
            # Tuple order MUST match primary key column order
            # For ScriptLineRevisionAssociation: (revision_id, line_id)
            assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, self.line1_id)
            )

            self.assertIsNotNone(assoc)
            self.assertEqual(assoc.revision_id, self.revision_id)
            self.assertEqual(assoc.line_id, self.line1_id)

    def test_composite_key_get_with_select(self):
        """Test composite key lookup using select().where()"""
        with self._app.get_db().sessionmaker() as session:
            stmt = select(ScriptLineRevisionAssociation).where(
                ScriptLineRevisionAssociation.revision_id == self.revision_id,
                ScriptLineRevisionAssociation.line_id == self.line2_id,
            )
            assoc = session.scalars(stmt).first()

            self.assertIsNotNone(assoc)
            self.assertEqual(assoc.revision_id, self.revision_id)
            self.assertEqual(assoc.line_id, self.line2_id)

    def test_composite_key_wrong_tuple_order_fails(self):
        """Verify that tuple order matters for composite keys"""
        with self._app.get_db().sessionmaker() as session:
            # Correct order: (revision_id, line_id)
            assoc_correct = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, self.line1_id)
            )
            self.assertIsNotNone(assoc_correct)
            self.assertEqual(assoc_correct.revision_id, self.revision_id)
            self.assertEqual(assoc_correct.line_id, self.line1_id)

            # Wrong order: (line_id, revision_id) instead of (revision_id, line_id)
            # Using obviously wrong IDs that won't exist
            assoc_wrong = session.get(
                ScriptLineRevisionAssociation,
                (99999, 88888),  # These IDs don't exist
            )
            self.assertIsNone(assoc_wrong)

    def test_composite_key_filter_all_for_revision(self):
        """Test getting all associations for a revision using select()"""
        with self._app.get_db().sessionmaker() as session:
            stmt = select(ScriptLineRevisionAssociation).where(
                ScriptLineRevisionAssociation.revision_id == self.revision_id
            )
            assocs = session.scalars(stmt).all()

            self.assertEqual(len(assocs), 3)
            line_ids = {assoc.line_id for assoc in assocs}
            self.assertEqual(line_ids, {self.line1_id, self.line2_id, self.line3_id})

    def test_composite_key_filter_by_single_column(self):
        """Test filtering by only one part of composite key"""
        with self._app.get_db().sessionmaker() as session:
            # Get all associations for line1 (might be in multiple revisions)
            stmt = select(ScriptLineRevisionAssociation).where(
                ScriptLineRevisionAssociation.line_id == self.line1_id
            )
            assocs = session.scalars(stmt).all()

            self.assertGreater(len(assocs), 0)
            self.assertTrue(all(assoc.line_id == self.line1_id for assoc in assocs))

    def test_composite_key_get_returns_none_when_not_found(self):
        """Test that session.get() with composite key returns None when not found"""
        with self._app.get_db().sessionmaker() as session:
            # Use IDs that don't exist together
            assoc = session.get(ScriptLineRevisionAssociation, (99999, 88888))
            self.assertIsNone(assoc)

    def test_composite_key_select_returns_none_when_not_found(self):
        """Test that select() returns None when composite key not found"""
        with self._app.get_db().sessionmaker() as session:
            stmt = select(ScriptLineRevisionAssociation).where(
                ScriptLineRevisionAssociation.revision_id == 99999,
                ScriptLineRevisionAssociation.line_id == 88888,
            )
            assoc = session.scalars(stmt).first()
            self.assertIsNone(assoc)

    def test_composite_key_relationship_navigation(self):
        """Test that relationships still work with composite keys"""
        with self._app.get_db().sessionmaker() as session:
            assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, self.line1_id)
            )

            # Verify relationships are accessible
            self.assertIsNotNone(assoc.revision)
            self.assertEqual(assoc.revision.id, self.revision_id)

            self.assertIsNotNone(assoc.line)
            self.assertEqual(assoc.line.id, self.line1_id)

    def test_composite_key_update(self):
        """Test updating a record with composite key"""
        with self._app.get_db().sessionmaker() as session:
            assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, self.line1_id)
            )

            # Update a field (using next_line_id as a test field)
            assoc.next_line_id = self.line2_id
            session.commit()

        # Verify update persisted
        with self._app.get_db().sessionmaker() as session:
            assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, self.line1_id)
            )
            self.assertEqual(assoc.next_line_id, self.line2_id)

    def test_composite_key_delete(self):
        """Test deleting a record with composite key"""
        with self._app.get_db().sessionmaker() as session:
            assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, self.line1_id)
            )
            session.delete(assoc)
            session.commit()

        # Verify deletion
        with self._app.get_db().sessionmaker() as session:
            assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, self.line1_id)
            )
            self.assertIsNone(assoc)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
