"""Tests for the composite FK constraints on ScriptLineRevisionAssociation.

The constraints (added by migration c2f8d4a6e0b3) enforce that next_line_id
and previous_line_id always reference a line within the same revision:

  (revision_id, next_line_id)     → (revision_id, line_id)  DEFERRABLE INITIALLY DEFERRED
  (revision_id, previous_line_id) → (revision_id, line_id)  DEFERRABLE INITIALLY DEFERRED

These tests use skip_migrations=True (in-memory SQLite), so constraints are
present because __table_args__ in ScriptLineRevisionAssociation includes them.
FK enforcement is enabled via the PRAGMA foreign_keys=ON event listener in
utils/database.py.

DEFERRED constraints: the IntegrityError fires at session.commit() (end of
the `with` block), not at flush time.
"""

from sqlalchemy.exc import IntegrityError

from models.script import (
    Script,
    ScriptLine,
    ScriptLineRevisionAssociation,
    ScriptLineType,
    ScriptRevision,
)
from models.show import Show, ShowScriptType
from test.conftest import DigiScriptTestCase


class TestRevisionLinkedListFKConstraints(DigiScriptTestCase):
    """Verify the composite self-referential FK constraints on
    script_line_revision_association are enforced by SQLite."""

    def _create_show_script_revision(self, session, revision_num=1):
        """Helper: create show → script → revision, return (script_id, revision_id)."""
        show = Show(name=f"Test Show {revision_num}", script_mode=ShowScriptType.FULL)
        session.add(show)
        session.flush()

        script = Script(show_id=show.id)
        session.add(script)
        session.flush()

        revision = ScriptRevision(
            script_id=script.id, revision=revision_num, description=f"Rev {revision_num}"
        )
        session.add(revision)
        session.flush()

        script.current_revision = revision.id
        return script.id, revision.id

    def _make_line(self, session, page=1):
        """Helper: create a bare ScriptLine (no act/scene required)."""
        line = ScriptLine(
            act_id=None,
            scene_id=None,
            page=page,
            line_type=ScriptLineType.DIALOGUE,
        )
        session.add(line)
        session.flush()
        return line.id

    def test_null_pointers_always_valid(self):
        """A single-line revision with NULL next/prev commits without error."""
        with self._app.get_db().sessionmaker() as session:
            _, revision_id = self._create_show_script_revision(session)
            line_id = self._make_line(session)

            assoc = ScriptLineRevisionAssociation(
                revision_id=revision_id,
                line_id=line_id,
                next_line_id=None,
                previous_line_id=None,
            )
            session.add(assoc)
            # No exception expected — NULL FK values are always valid

    def test_next_line_id_must_be_in_same_revision(self):
        """next_line_id pointing to a line in a different revision raises IntegrityError."""
        # Set up: two revisions, each with one line
        with self._app.get_db().sessionmaker() as session:
            _, revision_a_id = self._create_show_script_revision(session, 1)
            line_a_id = self._make_line(session, page=1)
            assoc_a = ScriptLineRevisionAssociation(
                revision_id=revision_a_id,
                line_id=line_a_id,
                next_line_id=None,
                previous_line_id=None,
            )
            session.add(assoc_a)

            _, revision_b_id = self._create_show_script_revision(session, 2)
            line_b_id = self._make_line(session, page=1)
            assoc_b = ScriptLineRevisionAssociation(
                revision_id=revision_b_id,
                line_id=line_b_id,
                next_line_id=None,
                previous_line_id=None,
            )
            session.add(assoc_b)
            # Both associations committed cleanly so far

        # Now try to make revision A's line point to revision B's line
        with self.assertRaises(IntegrityError):
            with self._app.get_db().sessionmaker() as session:
                assoc = session.get(
                    ScriptLineRevisionAssociation,
                    {"revision_id": revision_a_id, "line_id": line_a_id},
                )
                # line_b_id exists in script_lines (satisfies the simple FK)
                # but (revision_a_id, line_b_id) does NOT exist in the association
                # table → composite FK violation fires at commit
                assoc.next_line_id = line_b_id

    def test_previous_line_id_must_be_in_same_revision(self):
        """previous_line_id pointing to a line in a different revision raises IntegrityError."""
        with self._app.get_db().sessionmaker() as session:
            _, revision_a_id = self._create_show_script_revision(session, 1)
            line_a_id = self._make_line(session, page=1)
            session.add(
                ScriptLineRevisionAssociation(
                    revision_id=revision_a_id,
                    line_id=line_a_id,
                    next_line_id=None,
                    previous_line_id=None,
                )
            )

            _, revision_b_id = self._create_show_script_revision(session, 2)
            line_b_id = self._make_line(session, page=1)
            session.add(
                ScriptLineRevisionAssociation(
                    revision_id=revision_b_id,
                    line_id=line_b_id,
                    next_line_id=None,
                    previous_line_id=None,
                )
            )

        with self.assertRaises(IntegrityError):
            with self._app.get_db().sessionmaker() as session:
                assoc = session.get(
                    ScriptLineRevisionAssociation,
                    {"revision_id": revision_a_id, "line_id": line_a_id},
                )
                # (revision_a_id, line_b_id) doesn't exist → composite FK violation
                assoc.previous_line_id = line_b_id

    def test_valid_chain_in_same_revision_accepted(self):
        """A well-formed 3-line chain within one revision commits cleanly.

        Because the constraints are DEFERRED, we can insert associations in any
        order (all with NULL pointers first) and then update the pointers — the
        FK check only runs at COMMIT time, when all rows are present.
        """
        with self._app.get_db().sessionmaker() as session:
            _, revision_id = self._create_show_script_revision(session)

            line1_id = self._make_line(session, page=1)
            line2_id = self._make_line(session, page=1)
            line3_id = self._make_line(session, page=1)

            # Insert with NULL pointers first (deferred FK allows this)
            for lid in (line1_id, line2_id, line3_id):
                session.add(
                    ScriptLineRevisionAssociation(
                        revision_id=revision_id,
                        line_id=lid,
                        next_line_id=None,
                        previous_line_id=None,
                    )
                )
            session.flush()

            # Now wire up the chain
            a1 = session.get(
                ScriptLineRevisionAssociation,
                {"revision_id": revision_id, "line_id": line1_id},
            )
            a2 = session.get(
                ScriptLineRevisionAssociation,
                {"revision_id": revision_id, "line_id": line2_id},
            )
            a3 = session.get(
                ScriptLineRevisionAssociation,
                {"revision_id": revision_id, "line_id": line3_id},
            )

            a1.next_line_id = line2_id
            a2.previous_line_id = line1_id
            a2.next_line_id = line3_id
            a3.previous_line_id = line2_id
            # All (revision_id, next/prev_line_id) pairs exist in the table
            # → commit succeeds
