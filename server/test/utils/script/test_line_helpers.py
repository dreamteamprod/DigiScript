"""Tests for ``create_new_line`` in ``utils.script.line_helpers``."""

from models.script import (
    Script,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptLineType,
    ScriptRevision,
)
from models.show import Act, Character, Scene, Show, ShowScriptType
from test.conftest import DigiScriptTestCase
from utils.script.line_helpers import create_new_line


class _ScriptTestSetup(DigiScriptTestCase):
    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()

            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()

            character = Character(show_id=show.id, name="Alice")
            session.add(character)
            session.flush()

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Rev"
            )
            session.add(revision)
            session.flush()
            script.current_revision = revision.id

            self.show_id = show.id
            self.act_id = act.id
            self.scene_id = scene.id
            self.character_id = character.id
            self.revision_id = revision.id

    def _seed_line(self, session, previous_assoc=None, page=1, text="Line"):
        """Insert a ScriptLine + part + association; return the association."""
        line = ScriptLine(
            act_id=self.act_id,
            scene_id=self.scene_id,
            page=page,
            line_type=ScriptLineType.STAGE_DIRECTION,
        )
        session.add(line)
        session.flush()

        part = ScriptLinePart(
            line_id=line.id, part_index=0, line_text=text, character_id=None
        )
        session.add(part)
        session.flush()

        assoc = ScriptLineRevisionAssociation(
            revision_id=self.revision_id, line_id=line.id
        )
        session.add(assoc)
        session.flush()

        if previous_assoc:
            previous_assoc.next_line = line
            assoc.previous_line = previous_assoc.line
            session.flush()

        return assoc

    def _new_line_dict(self, page=1, text="New line"):
        return {
            "act_id": self.act_id,
            "scene_id": self.scene_id,
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
                session, revision, self._new_line_dict(), last
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
                session, revision, self._new_line_dict(page=1, text="Inserted"), l1
            )

            session.refresh(l1)
            session.refresh(l2)

        # l1 -> new_line -> l2, in both directions, with nothing dropped.
        self.assertEqual(l1.next_line_id, new_line.id)
        self.assertEqual(new_assoc.previous_line_id, l1.line_id)
        self.assertEqual(new_assoc.next_line_id, l2.line_id)
        self.assertEqual(l2.previous_line_id, new_line.id)

    def test_insert_chain_remains_fully_walkable(self):
        """A full head-to-tail walk reaches every line after an insert."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            l1 = self._seed_line(session, page=1, text="L1")
            l2 = self._seed_line(session, previous_assoc=l1, page=2, text="L2")
            l3 = self._seed_line(session, previous_assoc=l2, page=2, text="L3")

            create_new_line(
                session, revision, self._new_line_dict(page=1, text="Inserted"), l1
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
