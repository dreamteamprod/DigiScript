"""JS Yjs ↔ pycrdt wire-format interop.

The client-v3 unit tests and these server tests each only round-trip against their own
Yjs implementation. These tests consume a diff produced by real Yjs
(``yjs_edit.json``, made on top of the pycrdt-built ``pycrdt_state.json``) and check
pycrdt applies it and reads the edited values back. See
``test/helpers/yjs_interop_fixture.py`` for how to regenerate both fixtures.
"""

import base64
import json

import pycrdt

from test.helpers.yjs_interop_fixture import (
    EDIT_FIXTURE,
    STATE_FIXTURE,
    build_fixture_doc,
)


def _load(path, key):
    return base64.b64decode(json.loads(path.read_text())[key])


def test_committed_state_fixture_matches_production_build_ydoc():
    """Guards against the committed state going stale relative to build_ydoc's shape."""
    fresh = build_fixture_doc()
    committed = pycrdt.Doc()
    committed.get("meta", type=pycrdt.Map)
    committed.get("pages", type=pycrdt.Map)
    committed.get("deleted_line_ids", type=pycrdt.Array)
    committed.apply_update(_load(STATE_FIXTURE, "state"))

    assert (
        committed.get("pages", type=pycrdt.Map).to_py()
        == fresh.get("pages", type=pycrdt.Map).to_py()
    )


def test_pycrdt_applies_a_real_yjs_diff_and_reads_edits_back():
    doc = pycrdt.Doc()
    doc.get("meta", type=pycrdt.Map)
    pages = doc.get("pages", type=pycrdt.Map)
    doc.get("deleted_line_ids", type=pycrdt.Array)
    doc.apply_update(_load(STATE_FIXTURE, "state"))

    doc.apply_update(_load(EDIT_FIXTURE, "diff"))

    first_line = pages["1"][0]
    assert str(first_line["parts"][0]["line_text"]) == "Hello there world"
    assert first_line["act_id"] == 9
    # Untouched content survives the merge.
    assert str(pages["1"][1]["parts"][0]["line_text"]) == "Héllo ☃ wörld"
    assert str(pages["2"][0]["parts"][0]["line_text"]) == "Second page"
