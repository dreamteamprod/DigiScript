"""Tests for Y.Doc → ScriptLine database conversion.

Covers ``_parse_db_id``, ``extract_lines_from_ydoc``, ``_has_line_changed``,
and ``_save_script_page`` in ``utils.script.ydoc_to_lines``.
"""

import uuid

import pycrdt
import pytest
from sqlalchemy import select

from models.cue import Cue, CueAssociation, CueType
from models.script import (
    Script,
    ScriptCuts,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptLineType,
    ScriptRevision,
)
from models.show import Act, Character, Scene, Show, ShowScriptType
from test.conftest import DigiScriptTestCase
from utils.script.ydoc_to_lines import (
    _has_line_changed,
    _parse_db_id,
    _save_script_page,
    extract_lines_from_ydoc,
)


# ---------------------------------------------------------------------------
# TestParseDbId — pure unit, no DB
# ---------------------------------------------------------------------------


class TestParseDbId:
    def test_integer_string(self):
        assert _parse_db_id("5") == 5

    def test_uuid_string(self):
        assert _parse_db_id("c6b5e91b-055f-4a2f-8ab0-1234567890ab") is None

    def test_zero_string(self):
        assert _parse_db_id("0") is None

    def test_integer_zero(self):
        assert _parse_db_id(0) is None

    def test_float_like_string(self):
        assert _parse_db_id("3.0") == 3

    def test_uuid_starting_with_digit(self):
        # The leading digit must NOT be returned as an integer id
        assert _parse_db_id("3f1e2dbc-1234-5678-90ab-cdef01234567") is None

    def test_none(self):
        assert _parse_db_id(None) is None

    def test_negative(self):
        assert _parse_db_id("-1") is None


# ---------------------------------------------------------------------------
# Helpers for building Y.Doc structures in tests
# ---------------------------------------------------------------------------


def _build_empty_doc():
    """Create a properly initialised pycrdt Doc with all top-level types."""
    doc = pycrdt.Doc()
    doc.get("meta", type=pycrdt.Map)
    doc.get("pages", type=pycrdt.Map)
    doc.get("deleted_line_ids", type=pycrdt.Array)
    return doc


def _add_line_to_doc(
    doc,
    page_key,
    line_id,
    act_id=1,
    scene_id=1,
    line_type=2,
    stage_direction_style_id=0,
    parts=None,
):
    """Add a line Y.Map to ``pages[page_key]`` in *doc*, creating the page if needed."""
    pages = doc.get("pages", type=pycrdt.Map)
    if page_key not in pages:
        page_array = pycrdt.Array()
        pages[page_key] = page_array
    page_array = pages[page_key]

    line_map = pycrdt.Map()
    page_array.append(line_map)
    line_map["_id"] = str(line_id)
    line_map["act_id"] = act_id
    line_map["scene_id"] = scene_id
    line_map["line_type"] = line_type
    line_map["stage_direction_style_id"] = stage_direction_style_id

    parts_array = pycrdt.Array()
    line_map["parts"] = parts_array

    default_parts = [
        {
            "_id": "p1",
            "part_index": 0,
            "character_id": 0,
            "character_group_id": 0,
            "line_text": "text",
        }
    ]
    for p in parts if parts is not None else default_parts:
        part_map = pycrdt.Map()
        parts_array.append(part_map)
        part_map["_id"] = str(p.get("_id", "p1"))
        part_map["part_index"] = p.get("part_index", 0)
        part_map["character_id"] = p.get("character_id", 0)
        part_map["character_group_id"] = p.get("character_group_id", 0)
        part_map["line_text"] = pycrdt.Text(p.get("line_text", "text"))

    return line_map


# ---------------------------------------------------------------------------
# TestExtractLinesFromYdoc — pure unit, no DB
# ---------------------------------------------------------------------------


class TestExtractLinesFromYdoc:
    def test_empty_doc_returns_empty_lists(self):
        doc = _build_empty_doc()
        lines_by_page, deleted_ids = extract_lines_from_ydoc(doc)
        assert lines_by_page == []
        assert deleted_ids == []

    def test_single_page_two_lines(self):
        doc = _build_empty_doc()
        _add_line_to_doc(doc, "1", "10")
        _add_line_to_doc(doc, "1", "11")
        lines_by_page, _ = extract_lines_from_ydoc(doc)
        assert len(lines_by_page) == 1
        assert lines_by_page[0]["page"] == 1
        assert len(lines_by_page[0]["lines"]) == 2
        assert lines_by_page[0]["lines"][0]["_id"] == "10"
        assert lines_by_page[0]["lines"][1]["_id"] == "11"

    def test_line_fields_extracted(self):
        doc = _build_empty_doc()
        _add_line_to_doc(
            doc,
            "2",
            "5",
            act_id=3,
            scene_id=4,
            line_type=1,
            stage_direction_style_id=7,
            parts=[
                {
                    "_id": "p99",
                    "part_index": 0,
                    "character_id": 2,
                    "character_group_id": 0,
                    "line_text": "Hello",
                }
            ],
        )
        lines_by_page, _ = extract_lines_from_ydoc(doc)
        line = lines_by_page[0]["lines"][0]
        assert line["_id"] == "5"
        assert line["act_id"] == 3
        assert line["scene_id"] == 4
        assert line["line_type"] == 1
        assert line["stage_direction_style_id"] == 7
        assert len(line["line_parts"]) == 1
        assert line["line_parts"][0]["_id"] == "p99"
        assert line["line_parts"][0]["character_id"] == 2
        assert line["line_parts"][0]["line_text"] == "Hello"

    def test_multi_part_line_parts_in_order(self):
        doc = _build_empty_doc()
        _add_line_to_doc(
            doc,
            "1",
            "1",
            parts=[
                {
                    "_id": "pA",
                    "part_index": 0,
                    "character_id": 1,
                    "character_group_id": 0,
                    "line_text": "First",
                },
                {
                    "_id": "pB",
                    "part_index": 1,
                    "character_id": 2,
                    "character_group_id": 0,
                    "line_text": "Second",
                },
            ],
        )
        lines_by_page, _ = extract_lines_from_ydoc(doc)
        parts = lines_by_page[0]["lines"][0]["line_parts"]
        assert len(parts) == 2
        assert parts[0]["_id"] == "pA"
        assert parts[0]["part_index"] == 0
        assert parts[0]["line_text"] == "First"
        assert parts[1]["_id"] == "pB"
        assert parts[1]["part_index"] == 1

    def test_deleted_line_ids_integer_included(self):
        doc = _build_empty_doc()
        deleted = doc.get("deleted_line_ids", type=pycrdt.Array)
        deleted.append(42)
        _, deleted_ids = extract_lines_from_ydoc(doc)
        assert 42 in deleted_ids

    def test_deleted_line_ids_uuid_skipped(self):
        doc = _build_empty_doc()
        deleted = doc.get("deleted_line_ids", type=pycrdt.Array)
        deleted.append("c6b5e91b-055f-4a2f-8ab0-1234567890ab")
        _, deleted_ids = extract_lines_from_ydoc(doc)
        assert len(deleted_ids) == 0

    def test_act_id_zero_sentinel_becomes_none(self):
        doc = _build_empty_doc()
        _add_line_to_doc(doc, "1", "1", act_id=0)
        lines_by_page, _ = extract_lines_from_ydoc(doc)
        assert lines_by_page[0]["lines"][0]["act_id"] is None

    def test_multi_page_sorted_by_page_number(self):
        doc = _build_empty_doc()
        _add_line_to_doc(doc, "2", "20")
        _add_line_to_doc(doc, "1", "10")
        lines_by_page, _ = extract_lines_from_ydoc(doc)
        assert len(lines_by_page) == 2
        assert lines_by_page[0]["page"] == 1
        assert lines_by_page[0]["lines"][0]["_id"] == "10"
        assert lines_by_page[1]["page"] == 2
        assert lines_by_page[1]["lines"][0]["_id"] == "20"


# ---------------------------------------------------------------------------
# Shared DB setup base class for DB-backed tests
# ---------------------------------------------------------------------------


class _ScriptTestSetup(DigiScriptTestCase):
    """Seed a Show, Script, Revision, Act, Scene, Character for DB-backed tests."""

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


# ---------------------------------------------------------------------------
# TestHasLineChanged — DB-backed
# ---------------------------------------------------------------------------


class TestHasLineChanged(_ScriptTestSetup):
    """Tests for ``_has_line_changed`` using a real in-memory DB row."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            line = ScriptLine(
                act_id=self.act_id,
                scene_id=self.scene_id,
                page=1,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(line)
            session.flush()

            part = ScriptLinePart(
                line_id=line.id,
                part_index=0,
                character_id=self.character_id,
                character_group_id=None,
                line_text="Hello",
            )
            session.add(part)
            session.flush()

            assoc = ScriptLineRevisionAssociation(
                revision_id=self.revision_id,
                line_id=line.id,
            )
            session.add(assoc)
            self.line_id = line.id
            self.part_id = part.id

    def _make_ydoc_line(self, **overrides):
        """Return a Y.Doc line dict matching the DB content by default."""
        base = {
            "_id": str(self.line_id),
            "act_id": self.act_id,
            "scene_id": self.scene_id,
            "line_type": ScriptLineType.DIALOGUE.value,
            "stage_direction_style_id": None,
            "line_parts": [
                {
                    "_id": str(self.part_id),
                    "part_index": 0,
                    "character_id": self.character_id,
                    "character_group_id": None,
                    "line_text": "Hello",
                }
            ],
        }
        base.update(overrides)
        return base

    def test_identical_content_returns_false(self):
        with self._app.get_db().sessionmaker() as session:
            assert (
                _has_line_changed(self._make_ydoc_line(), self.line_id, session)
                is False
            )

    def test_text_changed_returns_true(self):
        line = self._make_ydoc_line(
            line_parts=[
                {
                    "_id": str(self.part_id),
                    "part_index": 0,
                    "character_id": self.character_id,
                    "character_group_id": None,
                    "line_text": "Changed!",
                }
            ]
        )
        with self._app.get_db().sessionmaker() as session:
            assert _has_line_changed(line, self.line_id, session) is True

    def test_act_changed_returns_true(self):
        with self._app.get_db().sessionmaker() as session:
            assert (
                _has_line_changed(
                    self._make_ydoc_line(act_id=999), self.line_id, session
                )
                is True
            )

    def test_scene_changed_returns_true(self):
        with self._app.get_db().sessionmaker() as session:
            assert (
                _has_line_changed(
                    self._make_ydoc_line(scene_id=999), self.line_id, session
                )
                is True
            )

    def test_line_type_changed_returns_true(self):
        with self._app.get_db().sessionmaker() as session:
            assert (
                _has_line_changed(
                    self._make_ydoc_line(
                        line_type=ScriptLineType.STAGE_DIRECTION.value
                    ),
                    self.line_id,
                    session,
                )
                is True
            )

    def test_stage_direction_style_changed_returns_true(self):
        with self._app.get_db().sessionmaker() as session:
            assert (
                _has_line_changed(
                    self._make_ydoc_line(stage_direction_style_id=99),
                    self.line_id,
                    session,
                )
                is True
            )

    def test_part_count_changed_returns_true(self):
        line = self._make_ydoc_line(
            line_parts=[
                {
                    "_id": str(self.part_id),
                    "part_index": 0,
                    "character_id": self.character_id,
                    "character_group_id": None,
                    "line_text": "Hello",
                },
                {
                    "_id": str(uuid.uuid4()),
                    "part_index": 1,
                    "character_id": self.character_id,
                    "character_group_id": None,
                    "line_text": "Extra",
                },
            ]
        )
        with self._app.get_db().sessionmaker() as session:
            assert _has_line_changed(line, self.line_id, session) is True

    def test_character_changed_returns_true(self):
        line = self._make_ydoc_line(
            line_parts=[
                {
                    "_id": str(self.part_id),
                    "part_index": 0,
                    "character_id": 9999,
                    "character_group_id": None,
                    "line_text": "Hello",
                }
            ]
        )
        with self._app.get_db().sessionmaker() as session:
            assert _has_line_changed(line, self.line_id, session) is True

    def test_missing_db_row_raises_value_error(self):
        with self._app.get_db().sessionmaker() as session:
            with pytest.raises(ValueError):
                _has_line_changed(self._make_ydoc_line(), 99999, session)


# ---------------------------------------------------------------------------
# TestSaveScriptPage — DB-backed
# ---------------------------------------------------------------------------


class TestSaveScriptPage(_ScriptTestSetup):
    """Tests for ``_save_script_page`` using a real in-memory SQLite DB."""

    def _seed_line(
        self,
        session,
        previous_assoc=None,
        text="Direction text",
        character_id=None,
        line_type=ScriptLineType.STAGE_DIRECTION,
        page=1,
    ):
        """Insert ScriptLine + ScriptLinePart + SLRA; return the association."""
        line = ScriptLine(
            act_id=self.act_id,
            scene_id=self.scene_id,
            page=page,
            line_type=line_type,
        )
        session.add(line)
        session.flush()

        part = ScriptLinePart(
            line_id=line.id,
            part_index=0,
            character_id=character_id,
            character_group_id=None,
            line_text=text,
        )
        session.add(part)
        session.flush()

        assoc = ScriptLineRevisionAssociation(
            revision_id=self.revision_id,
            line_id=line.id,
        )
        session.add(assoc)
        session.flush()

        if previous_assoc:
            previous_assoc.next_line = line
            assoc.previous_line = previous_assoc.line
            session.flush()

        return assoc

    def _assoc_to_line_dict(self, assoc):
        """Build a Y.Doc line dict that exactly matches an existing association (no changes)."""
        line = assoc.line
        parts = sorted(line.line_parts, key=lambda p: p.part_index or 0)
        return {
            "_id": str(line.id),
            "act_id": line.act_id,
            "scene_id": line.scene_id,
            "line_type": line.line_type.value,
            "stage_direction_style_id": line.stage_direction_style_id,
            "line_parts": [
                {
                    "_id": str(p.id),
                    "part_index": p.part_index,
                    "character_id": p.character_id,
                    "character_group_id": p.character_group_id,
                    "line_text": p.line_text or "",
                }
                for p in parts
            ],
        }

    def _make_stage_direction_dict(self, line_id_str, text="Direction text"):
        """Build a plain Y.Doc line dict for a new STAGE_DIRECTION line (UUID id)."""
        return {
            "_id": line_id_str,
            "act_id": self.act_id,
            "scene_id": self.scene_id,
            "line_type": ScriptLineType.STAGE_DIRECTION.value,
            "stage_direction_style_id": None,
            "line_parts": [
                {
                    "_id": str(uuid.uuid4()),
                    "part_index": 0,
                    "character_id": None,
                    "character_group_id": None,
                    "line_text": text,
                }
            ],
        }

    # ------ New-line tests ------

    def test_new_line_creates_db_row(self):
        new_id = str(uuid.uuid4())
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            _, id_map, _ = _save_script_page(
                revision,
                1,
                [self._make_stage_direction_dict(new_id)],
                [],
                session,
                show,
                None,
            )
            lines = session.scalars(select(ScriptLine)).all()
        self.assertEqual(1, len(lines))
        self.assertIn(new_id, id_map)
        self.assertEqual(1, len(id_map))

    def test_new_lines_linked_list(self):
        uuids = [str(uuid.uuid4()) for _ in range(3)]
        page_data = [self._make_stage_direction_dict(u) for u in uuids]
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            _, id_map, _ = _save_script_page(
                revision, 1, page_data, [], session, show, None
            )

        with self._app.get_db().sessionmaker() as session:
            db_ids = [int(id_map[u]) for u in uuids]
            a0 = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, db_ids[0])
            )
            a1 = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, db_ids[1])
            )
            a2 = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, db_ids[2])
            )
        self.assertIsNone(a0.previous_line_id)
        self.assertEqual(a0.next_line_id, db_ids[1])
        self.assertEqual(a1.previous_line_id, db_ids[0])
        self.assertEqual(a1.next_line_id, db_ids[2])
        self.assertEqual(a2.previous_line_id, db_ids[1])
        self.assertIsNone(a2.next_line_id)

    def test_new_line_with_previous_line(self):
        """New line's first entry links back to the provided ``previous_line``."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            prev_assoc = self._seed_line(session)
            prev_line_id = prev_assoc.line_id
            new_id = str(uuid.uuid4())
            _, id_map, _ = _save_script_page(
                revision,
                1,
                [self._make_stage_direction_dict(new_id)],
                [],
                session,
                show,
                prev_assoc,
            )
            new_db_id = int(id_map[new_id])
            new_assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, new_db_id)
            )
        self.assertEqual(new_assoc.previous_line_id, prev_line_id)

    # ------ Unchanged-line tests ------

    def test_unchanged_line_no_new_row(self):
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            assoc = self._seed_line(session)
            page_data = [self._assoc_to_line_dict(assoc)]
            _, id_map, _ = _save_script_page(
                revision, 1, page_data, [], session, show, None
            )
            lines = session.scalars(select(ScriptLine)).all()
        self.assertEqual(1, len(lines))
        self.assertEqual({}, id_map)

    def test_unchanged_line_pointer_update_bridges_gap(self):
        """Lines 1 and 3 remain (line 2 handled elsewhere) → 1.next=3, 3.prev=1."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            a1 = self._seed_line(session, text="L1")
            a2 = self._seed_line(session, previous_assoc=a1, text="L2")
            a3 = self._seed_line(session, previous_assoc=a2, text="L3")

            page_data = [self._assoc_to_line_dict(a1), self._assoc_to_line_dict(a3)]
            _save_script_page(revision, 1, page_data, [], session, show, None)

            session.refresh(a1)
            session.refresh(a3)
        self.assertEqual(a1.next_line_id, a3.line_id)
        self.assertEqual(a3.previous_line_id, a1.line_id)

    # ------ Changed-line tests ------

    def test_changed_line_creates_new_row(self):
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            assoc = self._seed_line(session, text="Original")
            old_line_id = assoc.line_id

            line_dict = self._assoc_to_line_dict(assoc)
            line_dict["line_parts"][0]["line_text"] = "Changed"
            last_assoc, _, _ = _save_script_page(
                revision, 1, [line_dict], [], session, show, None
            )
            new_line_id = last_assoc.line.id
        self.assertNotEqual(new_line_id, old_line_id)

    def test_changed_line_old_row_orphan_deleted(self):
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            assoc = self._seed_line(session, text="Original")
            old_line_id = assoc.line_id

            line_dict = self._assoc_to_line_dict(assoc)
            line_dict["line_parts"][0]["line_text"] = "Updated"
            _save_script_page(revision, 1, [line_dict], [], session, show, None)

        with self._app.get_db().sessionmaker() as session:
            self.assertIsNone(session.get(ScriptLine, old_line_id))

    def test_changed_line_new_row_has_correct_parts(self):
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            assoc = self._seed_line(session, text="Original")

            line_dict = self._assoc_to_line_dict(assoc)
            line_dict["line_parts"][0]["line_text"] = "Updated text"
            last_assoc, _, _ = _save_script_page(
                revision, 1, [line_dict], [], session, show, None
            )
            new_part_text = last_assoc.line.line_parts[0].line_text
        self.assertEqual("Updated text", new_part_text)

    def test_changed_line_id_map_has_old_to_new_mapping(self):
        """Editing a line must populate new_line_id_map so save_draft() patches the Y.Doc."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            assoc = self._seed_line(session, text="Original")
            old_line_id = assoc.line_id

            line_dict = self._assoc_to_line_dict(assoc)
            line_dict["line_parts"][0]["line_text"] = "Changed"
            _, new_line_id_map, _ = _save_script_page(
                revision, 1, [line_dict], [], session, show, None
            )

        self.assertIn(str(old_line_id), new_line_id_map)
        new_line_id = int(new_line_id_map[str(old_line_id)])
        self.assertNotEqual(new_line_id, old_line_id)

    def test_changed_line_part_id_map_has_old_to_new_mapping(self):
        """Editing a line must populate new_part_id_map for its parts too."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            assoc = self._seed_line(session, text="Original")
            old_part_id = assoc.line.line_parts[0].id

            line_dict = self._assoc_to_line_dict(assoc)
            line_dict["line_parts"][0]["line_text"] = "Changed"
            _, _, new_part_id_map = _save_script_page(
                revision, 1, [line_dict], [], session, show, None
            )

        self.assertIn(str(old_part_id), new_part_id_map)
        new_part_id = int(new_part_id_map[str(old_part_id)])
        self.assertNotEqual(new_part_id, old_part_id)

    # ------ Deletion tests ------

    def test_delete_middle_line(self):
        """Lines 1,2,3; delete 2 → DB has 1+3, linked list 1→3."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            a1 = self._seed_line(session, text="L1")
            a2 = self._seed_line(session, previous_assoc=a1, text="L2")
            a3 = self._seed_line(session, previous_assoc=a2, text="L3")
            del_id = a2.line_id

            page_data = [self._assoc_to_line_dict(a1), self._assoc_to_line_dict(a3)]
            _save_script_page(revision, 1, page_data, [del_id], session, show, None)

        with self._app.get_db().sessionmaker() as session:
            self.assertIsNone(
                session.get(ScriptLineRevisionAssociation, (self.revision_id, del_id))
            )
            a1_post = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, a1.line_id)
            )
            a3_post = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, a3.line_id)
            )
        self.assertEqual(a1_post.next_line_id, a3.line_id)
        self.assertEqual(a3_post.previous_line_id, a1.line_id)

    def test_delete_first_line(self):
        """Delete line 1 → line 2 ``previous_line_id`` is None."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            a1 = self._seed_line(session, text="L1")
            a2 = self._seed_line(session, previous_assoc=a1, text="L2")
            del_id = a1.line_id

            page_data = [self._assoc_to_line_dict(a2)]
            _save_script_page(revision, 1, page_data, [del_id], session, show, None)

        with self._app.get_db().sessionmaker() as session:
            a2_post = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, a2.line_id)
            )
        self.assertIsNone(a2_post.previous_line_id)

    def test_delete_last_line(self):
        """Delete line 3 → line 2 ``next_line_id`` is None."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            a1 = self._seed_line(session, text="L1")
            a2 = self._seed_line(session, previous_assoc=a1, text="L2")
            a3 = self._seed_line(session, previous_assoc=a2, text="L3")
            del_id = a3.line_id

            page_data = [self._assoc_to_line_dict(a1), self._assoc_to_line_dict(a2)]
            _save_script_page(revision, 1, page_data, [del_id], session, show, None)

        with self._app.get_db().sessionmaker() as session:
            a2_post = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, a2.line_id)
            )
        self.assertIsNone(a2_post.next_line_id)

    def test_delete_line_not_on_this_page(self):
        """``deleted_id`` for a line on page 2 is silently skipped when saving page 1."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            assoc_p2 = self._seed_line(session, text="Page 2 line", page=2)
            p2_line_id = assoc_p2.line_id
            assoc_p1 = self._seed_line(session, text="Page 1 line", page=1)

            page_data = [self._assoc_to_line_dict(assoc_p1)]
            _save_script_page(revision, 1, page_data, [p2_line_id], session, show, None)

        with self._app.get_db().sessionmaker() as session:
            self.assertIsNotNone(
                session.get(
                    ScriptLineRevisionAssociation, (self.revision_id, p2_line_id)
                )
            )

    def test_delete_missing_assoc_skipped(self):
        """``deleted_id`` with no SLRA → no crash."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            orphan = ScriptLine(
                act_id=self.act_id,
                scene_id=self.scene_id,
                page=1,
                line_type=ScriptLineType.STAGE_DIRECTION,
            )
            session.add(orphan)
            session.flush()
            orphan_id = orphan.id
            # No SLRA for orphan — should not raise
            _save_script_page(revision, 1, [], [orphan_id], session, show, None)

    # ------ Migration tests ------

    def test_cue_association_migrated(self):
        """``CueAssociation`` on old ``line_id`` is migrated to new line after change."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            assoc = self._seed_line(session, text="Original")
            old_line_id = assoc.line_id

            cue_type = CueType(
                show_id=self.show_id, prefix="LX", description="Lighting", colour="#fff"
            )
            session.add(cue_type)
            session.flush()
            cue = Cue(cue_type_id=cue_type.id, ident="Q1")
            session.add(cue)
            session.flush()
            ca = CueAssociation(
                revision_id=self.revision_id, line_id=old_line_id, cue_id=cue.id
            )
            session.add(ca)
            session.flush()

            line_dict = self._assoc_to_line_dict(assoc)
            line_dict["line_parts"][0]["line_text"] = "Changed"
            last_assoc, _, _ = _save_script_page(
                revision, 1, [line_dict], [], session, show, None
            )
            new_line_id = last_assoc.line.id

            new_ca = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.revision_id == self.revision_id,
                    CueAssociation.cue_id == cue.id,
                )
            ).first()
        self.assertIsNotNone(new_ca)
        self.assertEqual(new_ca.line_id, new_line_id)

    def test_script_cuts_migrated(self):
        """``ScriptCuts`` on old ``line_part_id`` migrated to new part after change."""
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            assoc = self._seed_line(session, text="Original")
            old_part_id = assoc.line.line_parts[0].id

            sc = ScriptCuts(revision_id=self.revision_id, line_part_id=old_part_id)
            session.add(sc)
            session.flush()

            line_dict = self._assoc_to_line_dict(assoc)
            line_dict["line_parts"][0]["line_text"] = "Updated"
            last_assoc, _, _ = _save_script_page(
                revision, 1, [line_dict], [], session, show, None
            )
            new_part_id = last_assoc.line.line_parts[0].id

            new_cut = session.get(ScriptCuts, (new_part_id, self.revision_id))
            old_cut = session.get(ScriptCuts, (old_part_id, self.revision_id))
        self.assertIsNotNone(new_cut)
        self.assertIsNone(old_cut)

    # ------ Error tests ------

    def test_validation_failure_raises(self):
        """DIALOGUE line with no character or group → ``ValueError`` raised."""
        bad_line = {
            "_id": str(uuid.uuid4()),
            "act_id": self.act_id,
            "scene_id": self.scene_id,
            "line_type": ScriptLineType.DIALOGUE.value,
            "stage_direction_style_id": None,
            "line_parts": [
                {
                    "_id": str(uuid.uuid4()),
                    "part_index": 0,
                    "character_id": None,
                    "character_group_id": None,
                    "line_text": "Hello",
                }
            ],
        }
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show
            with pytest.raises(ValueError):
                _save_script_page(revision, 1, [bad_line], [], session, show, None)

    # ------ Multi-page test ------

    def test_multi_page_previous_line_carried(self):
        """Page 1 last line links forward to page 2 first line via ``previous_line``."""
        p1_id = str(uuid.uuid4())
        p2_id = str(uuid.uuid4())

        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)
            show = revision.script.show

            last_p1, id_map_p1, _ = _save_script_page(
                revision,
                1,
                [self._make_stage_direction_dict(p1_id)],
                [],
                session,
                show,
                None,
            )
            last_p2, id_map_p2, _ = _save_script_page(
                revision,
                2,
                [self._make_stage_direction_dict(p2_id)],
                [],
                session,
                show,
                last_p1,
            )

            p1_db_id = int(id_map_p1[p1_id])
            p2_db_id = int(id_map_p2[p2_id])

            p2_assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, p2_db_id)
            )
            p1_assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, p1_db_id)
            )
        self.assertEqual(p2_assoc.previous_line_id, p1_db_id)
        self.assertEqual(p1_assoc.next_line_id, p2_db_id)
