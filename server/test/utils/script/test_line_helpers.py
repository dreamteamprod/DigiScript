"""Tests for ``create_new_line`` in ``utils.script.line_helpers``."""

from models.script import ScriptLineRevisionAssociation, ScriptLineType, ScriptRevision
from test.utils.script.test_ydoc_to_lines import _ScriptTestSetup
from utils.script.line_helpers import create_new_line


def _new_line_dict(test_case, page=1, text="New line"):
    return {
        "act_id": test_case.act_id,
        "scene_id": test_case.scene_id,
        "page": page,
        "line_type": ScriptLineType.STAGE_DIRECTION.value,
        "stage_direction_style_id": None,
        "line_parts": [
            {
                "part_index": 0,
                "character_id": None,
                "character_group_id": None,
                "line_text": text,
            }
        ],
    }


class TestCreateNewLine(_ScriptTestSetup):
    def test_true_append_leaves_next_line_none(self):
        """Appending after the line that is genuinely last keeps next_line unset."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            last = self._seed_line(session, text="L1")
            assoc, line_obj = create_new_line(
                session, revision, _new_line_dict(self), last
            )
            session.refresh(last)
        self.assertIsNone(assoc.next_line_id)
        self.assertEqual(assoc.previous_line_id, last.line_id)
        self.assertEqual(last.next_line_id, line_obj.id)

    def test_insert_after_a_line_with_an_existing_next_preserves_the_chain(self):
        """Regression for the "stuck page" bug: appending a blank line to a page
        that is not the script's last page must not sever the chain to whatever
        already follows (e.g. the next page's first line)."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            l1 = self._seed_line(session, page=1, text="L1")
            l2 = self._seed_line(session, previous_assoc=l1, page=2, text="L2")

            new_assoc, new_line = create_new_line(
                session, revision, _new_line_dict(self, page=1, text="Inserted"), l1
            )

            session.refresh(l1)
            session.refresh(l2)

        # l1 -> new_line -> l2, in both directions, with nothing dropped.
        self.assertEqual(l1.next_line_id, new_line.id)
        self.assertEqual(new_assoc.previous_line_id, l1.line_id)
        self.assertEqual(new_assoc.next_line_id, l2.line_id)
        self.assertEqual(l2.previous_line_id, new_line.id)

    def test_insert_after_a_line_whose_next_has_no_association_raises(self):
        """previous_line.next_line pointing at a ScriptLine with no association
        in this revision means the chain is already broken ahead of this
        insert point — this must raise with context, not silently splice a
        dangling next_line_id and leave it to an opaque IntegrityError at
        commit."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            l1 = self._seed_line(session, page=1, text="L1")
            l2 = self._seed_line(session, previous_assoc=l1, page=2, text="L2")
            # Remove l2's association only — l1.next_line (the ScriptLine) and
            # the FK column still point at it, but it's no longer tracked.
            session.query(ScriptLineRevisionAssociation).filter_by(
                revision_id=self.revision_id, line_id=l2.line_id
            ).delete()
            session.flush()

            with self.assertRaises(ValueError):
                create_new_line(
                    session, revision, _new_line_dict(self, page=1, text="Inserted"), l1
                )
            # The test's own setup (deleting l2's association while l1 still
            # points at it) is itself an inconsistency the outer session
            # context manager would otherwise try to commit on exit.
            session.rollback()

    def test_insert_chain_remains_fully_walkable(self):
        """A full head-to-tail walk reaches every line after an insert."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            l1 = self._seed_line(session, page=1, text="L1")
            l2 = self._seed_line(session, previous_assoc=l1, page=2, text="L2")
            l3 = self._seed_line(session, previous_assoc=l2, page=2, text="L3")

            create_new_line(
                session, revision, _new_line_dict(self, page=1, text="Inserted"), l1
            )

            all_assocs = (
                session.query(ScriptLineRevisionAssociation)
                .filter_by(revision_id=self.revision_id)
                .all()
            )
            by_line = {a.line_id: a for a in all_assocs}
            heads = [a for a in all_assocs if a.previous_line_id is None]
            self.assertEqual(1, len(heads))

            walked = []
            current = heads[0]
            while current is not None:
                walked.append(current.line_id)
                current = by_line.get(current.next_line_id)

        self.assertEqual(len(all_assocs), len(walked))
        self.assertEqual(walked[-1], l3.line_id)
