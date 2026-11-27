"""Tests for the TRACE-level Y.Doc event decoder in ``utils.script.yjs_debug``."""

import pycrdt

from utils.script.yjs_debug import _path_str, _summarise_events


def _capture_events(mutate):
    """Run *mutate(pages)* against a fresh doc and return every observed event."""
    doc = pycrdt.Doc()
    pages = doc.get("pages", type=pycrdt.Map)
    captured: list = []
    pages.observe_deep(captured.extend)
    mutate(pages)
    return captured


def test_path_str_renders_array_indices_against_previous_segment():
    assert _path_str([]) == "<root>"
    assert _path_str(["1", 0, "parts", 2]) == "1[0]/parts[2]"
    assert _path_str([3]) == "[3]"


def test_summarise_map_key_changes_and_deletions():
    def mutate(pages):
        pages["1"] = pycrdt.Array()
        line = pycrdt.Map()
        pages["1"].append(line)
        line["n"] = 5
        line["long"] = "x" * 100
        del line["n"]

    lines = _summarise_events(_capture_events(mutate))
    joined = "\n".join(lines)

    assert "Map['1'] add = <Array len=1>" in joined
    assert f"Map['long'] add = {'x' * 60 + '…'!r}" in joined  # long strings are clipped
    assert "Map['n'] delete = <deleted, was 5.0>" in joined


def test_summarise_text_and_array_deltas():
    def mutate(pages):
        arr = pycrdt.Array()
        pages["1"] = arr
        text = pycrdt.Text("hello")
        arr.append(text)
        text += " world"
        del text[0:2]
        arr.append(pycrdt.Map())

    joined = "\n".join(_summarise_events(_capture_events(mutate)))

    assert "Text delta:" in joined
    assert "insert ' world'" in joined
    assert "delete 2" in joined
    assert "retain 5" in joined
    assert "Array delta:" in joined
    assert "insert 1 item(s)" in joined


def test_summarise_no_events_is_empty():
    assert _summarise_events([]) == []
