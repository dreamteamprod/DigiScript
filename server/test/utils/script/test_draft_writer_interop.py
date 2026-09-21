"""The client's draft writer against the server's real save-side reader.

``client-v3``'s ``draftWriterFixture.test.ts`` applies a realistic sequence of editor
operations (add / edit / delete / insert lines, add parts, change act/scene, write to
the trailing page) to the doc the server built, and commits the resulting Yjs update as
``writer_ops.json``. Here that update is applied in pycrdt and read back through
``extract_lines_from_ydoc`` — the first step of a collaborative save — so a change to
what the writer emits that the server can't read fails here, not in production.

Regenerate from ``client-v3/`` with
``npx vitest run -u src/js/yjs/draftWriterFixture.test.ts`` after regenerating
``pycrdt_state.json`` (see ``test/helpers/yjs_interop_fixture.py``).
"""

import base64
import hashlib
import json
from types import SimpleNamespace

import pycrdt

from models.show import ShowScriptType
from test.helpers.yjs_interop_fixture import FIXTURE_DIR, STATE_FIXTURE
from utils.script.line_helpers import validate_line
from utils.script.ydoc_to_lines import (
    _parse_db_id,
    _ydoc_line_to_dict,
    extract_lines_from_ydoc,
)


WRITER_FIXTURE = FIXTURE_DIR / "writer_ops.json"


def _doc_after_writer_ops() -> pycrdt.Doc:
    state = json.loads(STATE_FIXTURE.read_text())["state"]
    ops = json.loads(WRITER_FIXTURE.read_text())
    assert ops["base_sha256"] == hashlib.sha256(state.encode()).hexdigest(), (
        "writer_ops.json was made on a different pycrdt_state.json — regenerate it"
    )

    doc = pycrdt.Doc()
    doc.get("meta", type=pycrdt.Map)
    doc.get("pages", type=pycrdt.Map)
    doc.get("deleted_line_ids", type=pycrdt.Array)
    doc.apply_update(base64.b64decode(state))
    doc.apply_update(base64.b64decode(ops["diff"]))
    return doc


def _by_page(lines_by_page):
    return {page["page"]: page["lines"] for page in lines_by_page}


def _line(lines, line_id):
    return next(line for line in lines if line["_id"] == line_id)


def test_the_server_reads_every_edit_the_writer_made():
    lines_by_page, deleted = extract_lines_from_ydoc(_doc_after_writer_ops())
    pages = _by_page(lines_by_page)

    # Pages 1-3, including the empty trailing page the writer wrote its last line into.
    assert sorted(pages) == [1, 2, 3]

    # Page 1: stage direction inserted at the top, existing line edited, existing line
    # deleted, dialogue appended — in that order.
    assert [line["_id"] for line in pages[1]] == ["n-3", "1", "n-1"]

    direction = _line(pages[1], "n-3")
    assert direction["line_type"] == 2
    assert direction["stage_direction_style_id"] == 7
    assert (direction["act_id"], direction["scene_id"]) == (1, 2)
    assert direction["line_parts"] == [
        {
            "_id": "n-4",
            "part_index": 0,
            "character_id": None,
            "character_group_id": None,
            "line_text": "Enter stage left",
        }
    ]

    edited = _line(pages[1], "1")
    assert edited["line_parts"][0]["line_text"] == "Hello brave world"
    # Untouched fields survive the edit.
    assert edited["line_parts"][0]["character_id"] == 3

    dialogue = _line(pages[1], "n-1")
    assert dialogue["line_type"] == 1
    assert dialogue["stage_direction_style_id"] is None
    assert dialogue["line_parts"] == [
        {
            "_id": "n-2",
            "part_index": 0,
            "character_id": 3,
            "character_group_id": None,
            "line_text": "Brand new",
        }
    ]

    # Page 2: act/scene changed and a second part (a character group) added.
    moved = _line(pages[2], "3")
    assert (moved["act_id"], moved["scene_id"]) == (9, 8)
    assert [p["line_text"] for p in moved["line_parts"]] == ["Second page", "Chorus"]
    assert moved["line_parts"][1]["part_index"] == 1
    assert moved["line_parts"][1]["character_id"] is None
    assert moved["line_parts"][1]["character_group_id"] == 4

    # Page 3: the trailing page the server created now holds a spacing line, which
    # must have no parts (the validator rejects one).
    assert [line["_id"] for line in pages[3]] == ["n-6"]
    assert pages[3][0]["line_type"] == 4
    assert pages[3][0]["line_parts"] == []

    # The deleted saved line is reported for the server to delete; new lines never are.
    assert deleted == [2]


def test_new_lines_are_recognised_as_unsaved_and_existing_ones_as_saved():
    lines_by_page, _ = extract_lines_from_ydoc(_doc_after_writer_ops())
    pages = _by_page(lines_by_page)

    # The save path creates a line when _parse_db_id gives None and updates it when it
    # gives a DB id, so the writer's ids must land on the right side of that line.
    assert _parse_db_id(_line(pages[1], "n-1")["_id"]) is None
    assert _parse_db_id(_line(pages[1], "1")["_id"]) == 1
    assert _parse_db_id(_line(pages[2], "3")["_id"]) == 3


def test_every_line_in_the_fixture_passes_the_savers_validator():
    """Extraction alone proves the writer's output is readable, not that it can be
    saved: `_save_script_page` validates each new or changed line and aborts the whole
    save on one failure, so run the fixture's lines through the same validator.

    This proves the *fixture* (every line fully filled in) is saveable. It does not
    claim the writer's defaults are: a fresh dialogue line has no character and a fresh
    stage direction no text, so they fail validation until typed into. How to handle a
    half-typed line at save time (skip it, gate it in the UI, or report per line) is a
    Step 2 decision; see the plan.
    """
    lines_by_page, _ = extract_lines_from_ydoc(_doc_after_writer_ops())
    show = SimpleNamespace(script_mode=ShowScriptType.FULL)

    for page in lines_by_page:
        for line in page["lines"]:
            valid, error = validate_line(show, _ydoc_line_to_dict(line, page["page"]))
            assert valid, f"page {page['page']} line {line['_id']}: {error}"
