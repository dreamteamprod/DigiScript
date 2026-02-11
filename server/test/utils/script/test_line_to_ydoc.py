"""Tests for ScriptLine → Y.Doc conversion (build_ydoc).

Tests the Phase B (CPU-bound) conversion that takes plain dict data
and produces a pycrdt Y.Doc. No database needed — uses synthetic data.
"""

import base64

import pycrdt

from utils.script.line_to_ydoc import build_ydoc


def _make_line_data(
    line_id,
    next_line_id=None,
    previous_line_id=None,
    page=1,
    act_id=1,
    scene_id=1,
    line_type=1,
    stage_direction_style_id=None,
    parts=None,
):
    """Helper to build a single line data dict matching fetch_script_line_data output."""
    if parts is None:
        parts = [
            {
                "id": line_id * 10,
                "part_index": 0,
                "character_id": 1,
                "character_group_id": None,
                "line_text": f"Line {line_id} text",
            }
        ]
    return {
        "line_id": line_id,
        "next_line_id": next_line_id,
        "previous_line_id": previous_line_id,
        "line": {
            "id": line_id,
            "act_id": act_id,
            "scene_id": scene_id,
            "page": page,
            "line_type": line_type,
            "stage_direction_style_id": stage_direction_style_id,
            "line_parts": parts,
        },
    }


class TestBuildYdocEmpty:
    def test_empty_script_returns_doc_with_empty_pages(self):
        doc = build_ydoc([], revision_id=42)

        meta = doc.get("meta", type=pycrdt.Map)
        pages = doc.get("pages", type=pycrdt.Map)

        assert meta["revision_id"] == 42
        assert len(pages) == 0

    def test_empty_script_has_deleted_line_ids_array(self):
        doc = build_ydoc([], revision_id=1)
        deleted = doc.get("deleted_line_ids", type=pycrdt.Array)
        assert len(deleted) == 0


class TestBuildYdocSingleLine:
    def test_single_line_creates_one_page(self):
        data = [_make_line_data(line_id=1, page=1)]
        doc = build_ydoc(data, revision_id=10)

        pages = doc.get("pages", type=pycrdt.Map)
        assert "1" in pages
        page_lines = pages["1"]
        assert len(page_lines) == 1

    def test_single_line_has_correct_fields(self):
        data = [
            _make_line_data(
                line_id=5,
                page=2,
                act_id=3,
                scene_id=4,
                line_type=2,
                stage_direction_style_id=7,
            )
        ]
        doc = build_ydoc(data, revision_id=1)

        pages = doc.get("pages", type=pycrdt.Map)
        line = pages["2"][0]

        assert line["_id"] == "5"
        assert line["act_id"] == 3
        assert line["scene_id"] == 4
        assert line["line_type"] == 2
        assert line["stage_direction_style_id"] == 7


class TestBuildYdocLinkedList:
    def test_three_lines_on_same_page_in_order(self):
        """Lines are linked: 1 → 2 → 3, all on page 1."""
        data = [
            _make_line_data(line_id=1, next_line_id=2, previous_line_id=None, page=1),
            _make_line_data(line_id=2, next_line_id=3, previous_line_id=1, page=1),
            _make_line_data(line_id=3, next_line_id=None, previous_line_id=2, page=1),
        ]
        doc = build_ydoc(data, revision_id=1)

        pages = doc.get("pages", type=pycrdt.Map)
        page_lines = pages["1"]
        assert len(page_lines) == 3
        assert page_lines[0]["_id"] == "1"
        assert page_lines[1]["_id"] == "2"
        assert page_lines[2]["_id"] == "3"

    def test_lines_across_two_pages(self):
        """Lines span two pages: 1,2 on page 1; 3 on page 2."""
        data = [
            _make_line_data(line_id=1, next_line_id=2, previous_line_id=None, page=1),
            _make_line_data(line_id=2, next_line_id=3, previous_line_id=1, page=1),
            _make_line_data(line_id=3, next_line_id=None, previous_line_id=2, page=2),
        ]
        doc = build_ydoc(data, revision_id=1)

        pages = doc.get("pages", type=pycrdt.Map)
        assert len(pages["1"]) == 2
        assert len(pages["2"]) == 1
        assert pages["2"][0]["_id"] == "3"

    def test_unordered_input_still_traverses_correctly(self):
        """Input order doesn't matter — linked list is traversed by next_line_id."""
        data = [
            _make_line_data(line_id=3, next_line_id=None, previous_line_id=2, page=1),
            _make_line_data(line_id=1, next_line_id=2, previous_line_id=None, page=1),
            _make_line_data(line_id=2, next_line_id=3, previous_line_id=1, page=1),
        ]
        doc = build_ydoc(data, revision_id=1)

        pages = doc.get("pages", type=pycrdt.Map)
        ids = [pages["1"][i]["_id"] for i in range(3)]
        assert ids == ["1", "2", "3"]


class TestBuildYdocLineParts:
    def test_line_with_multiple_parts(self):
        parts = [
            {
                "id": 10,
                "part_index": 0,
                "character_id": 1,
                "character_group_id": None,
                "line_text": "Hello",
            },
            {
                "id": 11,
                "part_index": 1,
                "character_id": 2,
                "character_group_id": None,
                "line_text": " World",
            },
        ]
        data = [_make_line_data(line_id=1, page=1, parts=parts)]
        doc = build_ydoc(data, revision_id=1)

        pages = doc.get("pages", type=pycrdt.Map)
        line_parts = pages["1"][0]["line_parts"]
        assert len(line_parts) == 2
        assert str(line_parts[0]["line_text"]) == "Hello"
        assert str(line_parts[1]["line_text"]) == " World"
        assert line_parts[0]["character_id"] == 1
        assert line_parts[1]["character_id"] == 2

    def test_line_text_is_ytext_type(self):
        data = [_make_line_data(line_id=1, page=1)]
        doc = build_ydoc(data, revision_id=1)

        pages = doc.get("pages", type=pycrdt.Map)
        line_text = pages["1"][0]["line_parts"][0]["line_text"]
        assert isinstance(line_text, pycrdt.Text)


class TestBuildYdocNullHandling:
    def test_null_page_becomes_page_zero(self):
        data = [_make_line_data(line_id=1, page=None)]
        doc = build_ydoc(data, revision_id=1)

        pages = doc.get("pages", type=pycrdt.Map)
        assert "0" in pages
        assert len(pages["0"]) == 1

    def test_null_act_id_becomes_zero(self):
        data = [_make_line_data(line_id=1, act_id=None)]
        doc = build_ydoc(data, revision_id=1)

        pages = doc.get("pages", type=pycrdt.Map)
        assert pages["1"][0]["act_id"] == 0


class TestBase64RoundTrip:
    """Test that Y.Doc updates survive base64 encoding/decoding."""

    def test_full_state_base64_round_trip(self):
        data = [
            _make_line_data(line_id=1, next_line_id=2, previous_line_id=None, page=1),
            _make_line_data(line_id=2, next_line_id=None, previous_line_id=1, page=1),
        ]
        doc = build_ydoc(data, revision_id=99)

        # Encode to base64 (simulating WebSocket transport)
        state = doc.get_update()
        encoded = base64.b64encode(state).decode("ascii")

        # Decode and apply to fresh doc
        decoded = base64.b64decode(encoded)
        doc2 = pycrdt.Doc()
        doc2.get("meta", type=pycrdt.Map)
        doc2.get("pages", type=pycrdt.Map)
        doc2.get("deleted_line_ids", type=pycrdt.Array)
        doc2.apply_update(decoded)

        pages = doc2.get("pages", type=pycrdt.Map)
        assert pages["1"][0]["_id"] == "1"
        assert pages["1"][1]["_id"] == "2"
        assert doc2.get("meta", type=pycrdt.Map)["revision_id"] == 99

    def test_incremental_update_base64_round_trip(self):
        doc = build_ydoc([], revision_id=1)
        meta = doc.get("meta", type=pycrdt.Map)

        # Capture an incremental update
        updates = []
        sub = doc.observe(lambda e: updates.append(e.update))
        meta["last_saved_at"] = "2026-01-01T00:00:00Z"
        del sub

        assert len(updates) == 1
        encoded = base64.b64encode(updates[0]).decode("ascii")
        decoded = base64.b64decode(encoded)

        # Apply to a fresh synced doc
        doc2 = pycrdt.Doc()
        doc2.get("meta", type=pycrdt.Map)
        doc2.apply_update(doc.get_update())
        doc2.apply_update(decoded)

        meta2 = doc2.get("meta", type=pycrdt.Map)
        assert meta2["last_saved_at"] == "2026-01-01T00:00:00Z"


class TestCrdtConvergence:
    """Test that concurrent edits on separate Y.Doc instances converge."""

    def test_concurrent_text_edits_converge(self):
        """Two docs edit different fields on the same line → both changes present."""
        data = [_make_line_data(line_id=1, page=1)]
        doc1 = build_ydoc(data, revision_id=1)

        # Sync doc1 → doc2
        doc2 = pycrdt.Doc()
        doc2.get("pages", type=pycrdt.Map)
        doc2.get("meta", type=pycrdt.Map)
        doc2.get("deleted_line_ids", type=pycrdt.Array)
        doc2.apply_update(doc1.get_update())

        # Doc1 changes act_id
        doc1.get("pages", type=pycrdt.Map)["1"][0]["act_id"] = 99

        # Doc2 changes scene_id
        doc2.get("pages", type=pycrdt.Map)["1"][0]["scene_id"] = 88

        # Cross-sync
        sv1 = doc1.get_state()
        sv2 = doc2.get_state()
        doc1.apply_update(doc2.get_update(sv1))
        doc2.apply_update(doc1.get_update(sv2))

        # Both should have both changes
        p1 = doc1.get("pages", type=pycrdt.Map)["1"][0]
        p2 = doc2.get("pages", type=pycrdt.Map)["1"][0]
        assert p1["act_id"] == 99
        assert p1["scene_id"] == 88
        assert p2["act_id"] == 99
        assert p2["scene_id"] == 88

    def test_concurrent_text_inserts_converge(self):
        """Two docs insert text at the same position → both texts present."""
        data = [
            _make_line_data(
                line_id=1,
                page=1,
                parts=[
                    {
                        "id": 10,
                        "part_index": 0,
                        "character_id": 1,
                        "character_group_id": None,
                        "line_text": "",
                    }
                ],
            )
        ]
        doc1 = build_ydoc(data, revision_id=1)

        doc2 = pycrdt.Doc()
        doc2.get("pages", type=pycrdt.Map)
        doc2.get("meta", type=pycrdt.Map)
        doc2.get("deleted_line_ids", type=pycrdt.Array)
        doc2.apply_update(doc1.get_update())

        # Both type at position 0
        text1 = doc1.get("pages", type=pycrdt.Map)["1"][0]["line_parts"][0]["line_text"]
        text2 = doc2.get("pages", type=pycrdt.Map)["1"][0]["line_parts"][0]["line_text"]

        text1 += "Hello"
        text2 += "World"

        # Cross-sync
        sv1 = doc1.get_state()
        sv2 = doc2.get_state()
        doc1.apply_update(doc2.get_update(sv1))
        doc2.apply_update(doc1.get_update(sv2))

        # Both should converge to same value (order may vary)
        result1 = str(
            doc1.get("pages", type=pycrdt.Map)["1"][0]["line_parts"][0]["line_text"]
        )
        result2 = str(
            doc2.get("pages", type=pycrdt.Map)["1"][0]["line_parts"][0]["line_text"]
        )
        assert result1 == result2
        assert "Hello" in result1
        assert "World" in result1

    def test_offline_edit_and_reconnect(self):
        """Doc1 goes offline, both make edits, then sync → convergence."""
        data = [_make_line_data(line_id=1, page=1)]
        doc1 = build_ydoc(data, revision_id=1)

        doc2 = pycrdt.Doc()
        doc2.get("pages", type=pycrdt.Map)
        doc2.get("meta", type=pycrdt.Map)
        doc2.get("deleted_line_ids", type=pycrdt.Array)
        doc2.apply_update(doc1.get_update())

        # "Offline" period — both make independent changes
        doc1.get("pages", type=pycrdt.Map)["1"][0]["act_id"] = 10
        doc2.get("pages", type=pycrdt.Map)["1"][0]["scene_id"] = 20

        # "Reconnect" — exchange state
        sv1 = doc1.get_state()
        sv2 = doc2.get_state()
        doc1.apply_update(doc2.get_update(sv1))
        doc2.apply_update(doc1.get_update(sv2))

        p1 = doc1.get("pages", type=pycrdt.Map)["1"][0]
        p2 = doc2.get("pages", type=pycrdt.Map)["1"][0]
        assert p1["act_id"] == p2["act_id"] == 10
        assert p1["scene_id"] == p2["scene_id"] == 20
