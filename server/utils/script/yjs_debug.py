"""Trace-level decoding utilities for Y.Doc updates.

Attaches a deep observer to a ScriptRoom's ``pages`` map and
``deleted_line_ids`` array so that every field change applied to the
shared document is logged at TRACE level, regardless of whether it
arrived via ``YJS_UPDATE``, ``YJS_SYNC``, or a local save operation.

Enable by running the server with ``--logging=trace`` (or setting log
level to TRACE in config).  Has zero overhead when the TRACE level is
not enabled.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pycrdt

from digi_server.logger import get_logger


if TYPE_CHECKING:
    from utils.script_room_manager import ScriptRoom

# Custom TRACE level registered in main.py as logging.DEBUG - 5
TRACE = logging.DEBUG - 5


def _path_str(path) -> str:
    """Render an event path list as a compact string, e.g. ``page[1]/parts[0]``."""
    if not path:
        return "<root>"
    parts = []
    for segment in path:
        if isinstance(segment, int):
            # Array index — suffix the previous segment
            if parts:
                parts[-1] = f"{parts[-1]}[{segment}]"
            else:
                parts.append(f"[{segment}]")
        else:
            parts.append(str(segment))
    return "/".join(parts)


def _clip(text: str, limit: int) -> str:
    """Truncate *text* to *limit* characters, marking the cut with an ellipsis."""
    return text[:limit] + "…" if len(text) > limit else text


def _describe_value(val) -> str:
    """Render a Y.Doc value compactly for a log line."""
    if isinstance(val, (pycrdt.Map, pycrdt.Array)):
        return f"<{type(val).__name__} len={len(val)}>"
    if isinstance(val, pycrdt.Text):
        return repr(_clip(str(val), 60))
    if isinstance(val, str):
        return repr(_clip(val, 60))
    return repr(val)


def _describe_key_change(target, key, info) -> tuple[str, str]:
    """Describe one changed key of a ``MapEvent`` as ``(action, value string)``."""
    action = info.get("action", "?") if isinstance(info, dict) else str(info)
    try:
        if target is not None and action != "delete":
            val_str = _describe_value(target[key])
        else:
            old = info.get("oldValue", "?") if isinstance(info, dict) else "?"
            val_str = f"<deleted, was {old!r}>"
    except Exception as exc:
        val_str = f"<read-error: {exc}>"
    return action, val_str


def _describe_delta_op(op: dict) -> str | None:
    """Describe one delta operation, or ``None`` for an unrecognised op."""
    if "insert" in op:
        ins = op["insert"]
        if isinstance(ins, str):
            return f"insert {_clip(ins, 40)!r}"
        if isinstance(ins, list):
            return f"insert {len(ins)} item(s)"
        return f"insert {ins!r}"
    if "delete" in op:
        return f"delete {op['delete']}"
    if "retain" in op:
        return f"retain {op['retain']}"
    return None


def _summarise_event(event) -> list[str]:
    """Convert one pycrdt deep-observer event into readable strings."""
    lines = []
    target = getattr(event, "target", None)
    target_type = type(target).__name__ if target is not None else "?"
    path = _path_str(getattr(event, "path", None) or [])

    keys_changed = getattr(event, "keys", None)
    if keys_changed is not None:
        for key, info in keys_changed.items():
            action, val_str = _describe_key_change(target, key, info)
            lines.append(f"{target_type}[{key!r}] {action} = {val_str}  (path: {path})")

    delta = getattr(event, "delta", None)
    if delta is not None:
        parts = [d for d in map(_describe_delta_op, delta) if d is not None]
        lines.append(
            f"{target_type} delta: {', '.join(parts) or '(empty)'}  (path: {path})"
        )
    return lines


def _summarise_events(events) -> list[str]:
    """Convert a list of pycrdt deep-observer events into readable strings.

    Handles ``MapEvent`` (``keys`` dict), ``ArrayEvent`` and ``TextEvent``
    (``delta`` list).  Truncates long string values so logs stay readable.
    """
    return [line for event in events for line in _summarise_event(event)]


def make_pages_observer(revision_id: int):
    """Return a ``observe_deep`` callback for the ``pages`` Y.Map.

    Logs every nested change at TRACE level.  Safe to call even when TRACE is
    disabled — the body is guarded by ``isEnabledFor``.

    :param revision_id: Used as a prefix in log messages for easy filtering.
    """
    log = get_logger()

    def _observer(events):
        if not log.isEnabledFor(TRACE):
            return
        summaries = _summarise_events(events)
        for summary in summaries:
            log.trace(f"[ydoc pages rev={revision_id}] {summary}")

    return _observer


def make_deleted_ids_observer(revision_id: int):
    """Return an ``observe`` callback for the ``deleted_line_ids`` Y.Array.

    :param revision_id: Used as a prefix in log messages.
    """
    log = get_logger()

    def _observer(event):
        if not log.isEnabledFor(TRACE):
            return
        summaries = _summarise_events([event])
        for summary in summaries:
            log.trace(f"[ydoc deleted_ids rev={revision_id}] {summary}")

    return _observer


def attach_trace_observers(room: ScriptRoom) -> tuple:
    """Attach deep trace observers to *room*'s Y.Doc shared types.

    Returns a 2-tuple ``(pages_sub, deleted_sub)`` that the caller must hold
    a reference to (and ``del`` when done) to keep the observers alive.

    :param room: The :class:`ScriptRoom` to observe.
    :returns: ``(pages_subscription, deleted_ids_subscription)``
    """
    log = get_logger()
    if not log.isEnabledFor(TRACE):
        return None, None

    doc = room.doc
    pages_map = doc.get("pages", type=pycrdt.Map)
    deleted_arr = doc.get("deleted_line_ids", type=pycrdt.Array)

    pages_sub = pages_map.observe_deep(make_pages_observer(room.revision_id))
    deleted_sub = deleted_arr.observe(make_deleted_ids_observer(room.revision_id))

    log.trace(
        f"[ydoc rev={room.revision_id}] "
        f"Trace observers attached to pages map and deleted_line_ids array"
    )
    return pages_sub, deleted_sub
