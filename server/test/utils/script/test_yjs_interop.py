"""JS Yjs ↔ pycrdt wire-format interop.

The client-v3 unit tests and these server tests each only round-trip against their own
Yjs implementation. These tests consume a diff produced by real Yjs
(``yjs_edit.json``, made on top of the pycrdt-built ``pycrdt_state.json``) and check
pycrdt applies it and reads the edited values back. See
``test/helpers/yjs_interop_fixture.py`` for how to regenerate both fixtures.
"""

import base64
import hashlib
import json

import pycrdt

from test.helpers.yjs_interop_fixture import (
    EDIT_FIXTURE,
    STATE_FIXTURE,
    build_fixture_doc,
)


def _load(path, key):
    """Read a base64 field out of a committed fixture.

    :param path: The fixture JSON file.
    :param key: The field holding the base64-encoded Yjs update.
    :returns: The decoded update bytes.
    """
    return base64.b64decode(json.loads(path.read_text())[key])


def test_committed_state_fixture_matches_production_build_ydoc():
    """Guards against the committed state going stale relative to build_ydoc's shape."""
    fresh = build_fixture_doc()
    committed = pycrdt.Doc()
    committed.get("meta", type=pycrdt.Map)
    committed.get("pages", type=pycrdt.Map)
    committed.get("deleted_line_ids", type=pycrdt.Array)
    committed.apply_update(_load(STATE_FIXTURE, "state"))

    for name, type_ in (
        ("meta", pycrdt.Map),
        ("pages", pycrdt.Map),
        ("deleted_line_ids", pycrdt.Array),
    ):
        assert (
            committed.get(name, type=type_).to_py()
            == fresh.get(name, type=type_).to_py()
        ), (
            f"committed pycrdt_state.json is stale for '{name}' — regenerate the fixtures"
        )


def test_yjs_edit_fixture_was_made_on_the_committed_state():
    """A regenerated state with a stale edit would otherwise fail as a confusing text mismatch."""
    state = json.loads(STATE_FIXTURE.read_text())["state"]
    base = json.loads(EDIT_FIXTURE.read_text())["base_sha256"]

    assert base == hashlib.sha256(state.encode()).hexdigest(), (
        "yjs_edit.json was made on a different pycrdt_state.json — "
        "rerun node scripts/generate-yjs-interop-fixture.mjs"
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
