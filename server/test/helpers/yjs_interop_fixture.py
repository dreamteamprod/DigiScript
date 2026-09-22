"""Shared source of truth for the JS<->pycrdt Yjs interop fixtures.

Each side's unit tests only ever round-trip against themselves, so nothing else
would catch the two Yjs implementations drifting apart on the wire format. The
fixtures under ``client-v3/src/js/yjs/__fixtures__/`` are produced by real
pycrdt (via the production ``build_ydoc``) and real Yjs, are committed, and are
consumed by tests on the *other* side:

- ``pycrdt_state.json`` — full doc state built by ``build_ydoc``; consumed by
  client-v3's ``interop.test.ts``.
- ``yjs_edit.json`` — a Yjs diff made on top of that exact state; consumed by
  ``test_yjs_interop.py`` (it must be applied to the same base, so both are
  derived from one committed state).

Regenerate the pycrdt half from ``server/`` with::

    python -m test.helpers.yjs_interop_fixture

then the Yjs half from ``client-v3/`` with ``node scripts/generate-yjs-interop-fixture.mjs``.
"""

import base64
import json
from pathlib import Path

from utils.script.line_to_ydoc import build_ydoc


FIXTURE_DIR = (
    Path(__file__).resolve().parents[3]
    / "client-v3"
    / "src"
    / "js"
    / "yjs"
    / "__fixtures__"
)
STATE_FIXTURE = FIXTURE_DIR / "pycrdt_state.json"
EDIT_FIXTURE = FIXTURE_DIR / "yjs_edit.json"

REVISION_ID = 7


def _line(line_id, prev_id, next_id, page, text):
    """Build one ``fetch_script_line_data``-shaped dict with a single dialogue part.

    :param line_id: The line's DB id (the part id is derived as ``line_id * 10``).
    :param prev_id: Linked-list predecessor's line id, or None for the head.
    :param next_id: Linked-list successor's line id, or None for the tail.
    :param page: The page number the line sits on.
    :param text: The line part's text.
    :returns: A dict accepted by ``build_ydoc``.
    """
    return {
        "line_id": line_id,
        "previous_line_id": prev_id,
        "next_line_id": next_id,
        "line": {
            "id": line_id,
            "act_id": 1,
            "scene_id": 2,
            "page": page,
            "line_type": 1,
            "stage_direction_style_id": None,
            "line_parts": [
                {
                    "id": line_id * 10,
                    "part_index": 0,
                    "character_id": 3,
                    "character_group_id": None,
                    "line_text": text,
                }
            ],
        },
    }


def build_fixture_doc():
    """Build the doc both interop fixtures are derived from.

    Two pages, three lines — exercises 0-sentinel nulls, unicode and multiple pages.

    :returns: A ``pycrdt.Doc`` built by the production ``build_ydoc``.
    """
    return build_ydoc(
        [
            _line(1, None, 2, 1, "Hello world"),
            _line(2, 1, 3, 1, "Héllo ☃ wörld"),
            _line(3, 2, None, 2, "Second page"),
        ],
        REVISION_ID,
    )


def main():
    doc = build_fixture_doc()
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FIXTURE.write_text(
        json.dumps(
            {
                "revision_id": REVISION_ID,
                "state": base64.b64encode(doc.get_update()).decode("ascii"),
            },
            indent=2,
        )
        + "\n"
    )
    print(f"wrote {STATE_FIXTURE}")


if __name__ == "__main__":
    main()
