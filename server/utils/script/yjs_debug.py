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


def _summarise_events(events) -> list[str]:
    """Convert a list of pycrdt deep-observer events into readable strings.

    Handles ``MapEvent`` (``keys`` dict), ``ArrayEvent`` and ``TextEvent``
    (``delta`` list).  Truncates long string values so logs stay readable.
    """
    lines = []
    for event in events:
        target = getattr(event, "target", None)
        target_type = type(target).__name__ if target is not None else "?"
        path = _path_str(getattr(event, "path", None) or [])

        keys_changed = getattr(event, "keys", None)
        if keys_changed is not None:
            for key, info in keys_changed.items():
                action = (
                    info.get("action", "?") if isinstance(info, dict) else str(info)
                )
                try:
                    if target is not None and action != "delete":
                        val = target[key]
                        if isinstance(val, (pycrdt.Map, pycrdt.Array)):
                            val_str = f"<{type(val).__name__} len={len(val)}>"
                        elif isinstance(val, pycrdt.Text):
                            txt = str(val)
                            val_str = repr(txt[:60] + "…" if len(txt) > 60 else txt)
                        elif isinstance(val, str) and len(val) > 60:
                            val_str = repr(val[:60] + "…")
                        else:
                            val_str = repr(val)
                    else:
                        old = (
                            info.get("oldValue", "?") if isinstance(info, dict) else "?"
                        )
                        val_str = f"<deleted, was {old!r}>"
                except Exception as exc:
                    val_str = f"<read-error: {exc}>"
                lines.append(
                    f"{target_type}[{key!r}] {action} = {val_str}  (path: {path})"
                )

        delta = getattr(event, "delta", None)
        if delta is not None:
            parts = []
            for op in delta:
                if "insert" in op:
                    ins = op["insert"]
                    if isinstance(ins, str):
                        snippet = repr(ins[:40] + "…" if len(ins) > 40 else ins)
                        parts.append(f"insert {snippet}")
                    elif isinstance(ins, list):
                        parts.append(f"insert {len(ins)} item(s)")
                    else:
                        parts.append(f"insert {ins!r}")
                elif "delete" in op:
                    parts.append(f"delete {op['delete']}")
                elif "retain" in op:
                    parts.append(f"retain {op['retain']}")
            lines.append(
                f"{target_type} delta: {', '.join(parts) or '(empty)'}  (path: {path})"
            )

    return lines


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
