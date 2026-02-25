#!/usr/bin/env python3
"""Diagnose and optionally repair ScriptLineRevisionAssociation linked list integrity.

Runs two independent chain-walks for each revision:

  1. GLOBAL WALK  — starts at the head (previous_line_id IS NULL) and follows
     next_line_id until the chain ends or a broken pointer is detected.  Mirrors
     what build_ydoc does, but iteratively in Python so there is no SQL recursion
     depth limit.

  2. PAGE WALK    — for each distinct page value, finds the bridge line whose
     previous_line_id points to a line on page-1 (or is NULL for page 1), then
     walks next_line_id staying on that page.  Mirrors the logic in the GET
     /api/v1/show/script endpoint.

Comparing the two counts reveals whether orphans are truly unreachable or whether
the problem is only the cross-page pointer stitching (a smaller repair target).

Usage (run from the server/ directory):
    python3 utils/script/diagnose_linked_list.py
    python3 utils/script/diagnose_linked_list.py --revision-id 21
    python3 utils/script/diagnose_linked_list.py --verbose
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _open_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _get_db_path(args) -> str:
    if args.db_path:
        return args.db_path
    config_file = Path(os.path.join(os.path.dirname(__file__), "..", "conf/digiscript.json"))
    if config_file.exists():
        with config_file.open() as fh:
            cfg = json.load(fh)
        # Config stores an SQLAlchemy URL like "sqlite:////abs/path/to/file.sqlite"
        db_url = cfg.get("db_path", "")
        if db_url.startswith("sqlite:///"):
            raw = db_url[len("sqlite:///") :]
            return os.path.normpath(raw)
        if db_url:
            return db_url
    return "conf/digiscript.sqlite"


def _get_revision_ids(conn: sqlite3.Connection, revision_id: int | None) -> list[int]:
    if revision_id is not None:
        row = conn.execute(
            "SELECT id FROM script_revisions WHERE id = ?", (revision_id,)
        ).fetchone()
        if row is None:
            print(
                f"ERROR: revision {revision_id} not found in database.", file=sys.stderr
            )
            sys.exit(1)
        return [revision_id]
    rows = conn.execute("SELECT id FROM script_revisions ORDER BY id").fetchall()
    return [r["id"] for r in rows]


# ---------------------------------------------------------------------------
# Walk 1: global linked-list traversal (mirrors build_ydoc)
# ---------------------------------------------------------------------------


def _global_walk(
    conn: sqlite3.Connection, revision_id: int
) -> tuple[list[int], str | None]:
    """Return (visited_line_ids_in_order, break_reason_or_None)."""
    rows = conn.execute(
        "SELECT line_id, next_line_id, previous_line_id "
        "FROM script_line_revision_association WHERE revision_id = ?",
        (revision_id,),
    ).fetchall()

    by_id: dict[int, dict] = {
        r["line_id"]: {"next": r["next_line_id"], "prev": r["previous_line_id"]}
        for r in rows
    }

    # An empty revision is valid — nothing to walk
    if not by_id:
        return [], None

    # Find head — exactly one row should have previous_line_id IS NULL
    heads = [lid for lid, d in by_id.items() if d["prev"] is None]
    if not heads:
        return [], "no head found (no row with previous_line_id IS NULL)"

    if len(heads) > 1:
        head_ids = ", ".join(str(h) for h in heads[:5])
        if len(heads) > 5:
            head_ids += f", ... ({len(heads) - 5} more)"
        return [], f"multiple heads ({len(heads)} found: {head_ids})"

    visited: list[int] = []
    seen: set[int] = set()
    current = heads[0]
    break_reason: str | None = None

    while current is not None:
        if current in seen:
            break_reason = f"loop detected at line_id={current}"
            break
        if current not in by_id:
            break_reason = f"pointer leads to line_id={current} which is not in revision {revision_id}"
            break
        seen.add(current)
        visited.append(current)
        current = by_id[current]["next"]

    return visited, break_reason


# ---------------------------------------------------------------------------
# Walk 2: page-local traversal (mirrors GET /api/v1/show/script?page=N)
# ---------------------------------------------------------------------------


def _page_walk(conn: sqlite3.Connection, revision_id: int) -> dict[int, list[int]]:
    """Return {page: [line_id_in_order]} using page-boundary bridge detection.

    Bridge detection mirrors the GET endpoint: the first line of page N is the
    line whose previous_line_id points to a line on page N-1 (looking up the
    page directly from script_lines, not from the revision associations — the
    previous line may have been deleted from this revision while still existing
    in script_lines).
    """
    rows = conn.execute(
        """
        SELECT a.line_id, a.next_line_id, a.previous_line_id,
               l.page AS page,
               lp.page AS prev_page
        FROM script_line_revision_association a
        JOIN script_lines l ON l.id = a.line_id
        LEFT JOIN script_lines lp ON lp.id = a.previous_line_id
        WHERE a.revision_id = ?
        """,
        (revision_id,),
    ).fetchall()

    # Group by page
    by_page: dict[int, dict[int, dict]] = defaultdict(dict)
    for r in rows:
        page = r["page"] if r["page"] is not None else 0
        by_page[page][r["line_id"]] = {
            "next": r["next_line_id"],
            "prev": r["previous_line_id"],
            "prev_page": r["prev_page"],
        }

    result: dict[int, list[int]] = {}

    for page in sorted(by_page.keys()):
        page_lines = by_page[page]

        # Find the bridge line:
        #   - previous_line_id IS NULL  (global head), or
        #   - previous_line.page == page - 1  (cross-page pointer)
        # The prev_page is read from script_lines directly, so it is valid even
        # when the previous line was removed from this revision's associations.
        first_line_id: int | None = None
        for line_id, d in page_lines.items():
            prev_id = d["prev"]
            prev_page = d["prev_page"]
            if prev_id is None or (prev_page is not None and prev_page == page - 1):
                first_line_id = line_id
                break

        if first_line_id is None:
            result[page] = []
            continue

        # Walk within this page following next_line_id
        ordered: list[int] = []
        current = first_line_id
        seen: set[int] = set()
        while current is not None and current in page_lines:
            if current in seen:
                break  # loop guard
            seen.add(current)
            ordered.append(current)
            current = page_lines[current]["next"]

        result[page] = ordered

    return result


# ---------------------------------------------------------------------------
# Diagnostics report
# ---------------------------------------------------------------------------


def diagnose_revision(
    conn: sqlite3.Connection, revision_id: int, verbose: bool = False
) -> dict:
    """Run both walks for one revision and return a summary dict."""
    total = conn.execute(
        "SELECT COUNT(*) FROM script_line_revision_association WHERE revision_id = ?",
        (revision_id,),
    ).fetchone()[0]

    global_visited, break_reason = _global_walk(conn, revision_id)
    page_ordered = _page_walk(conn, revision_id)

    global_count = len(global_visited)
    page_total = sum(len(v) for v in page_ordered.values())
    page_count = len(page_ordered)

    # Lines reachable via page walk but NOT via global walk
    global_set = set(global_visited)
    page_set = {lid for lids in page_ordered.values() for lid in lids}
    in_page_not_global = page_set - global_set
    in_global_not_page = global_set - page_set

    # Per-page anomalies: pages where page-walk didn't return all lines
    page_anomalies: dict[int, dict] = {}
    for page in sorted(page_ordered.keys()):
        all_on_page = conn.execute(
            """
            SELECT COUNT(*) FROM script_line_revision_association a
            JOIN script_lines l ON l.id = a.line_id
            WHERE a.revision_id = ? AND l.page = ?
            """,
            (revision_id, page),
        ).fetchone()[0]
        reached = len(page_ordered[page])
        if reached != all_on_page:
            page_anomalies[page] = {"reached": reached, "total": all_on_page}

    return {
        "revision_id": revision_id,
        "total_assocs": total,
        "global_reachable": global_count,
        "global_break": break_reason,
        "page_reachable": page_total,
        "num_pages": page_count,
        "in_page_not_global": len(in_page_not_global),
        "in_global_not_page": len(in_global_not_page),
        "page_anomalies": page_anomalies,
    }


def print_report(result: dict, verbose: bool = False) -> None:
    rev_id = result["revision_id"]
    total = result["total_assocs"]
    g = result["global_reachable"]
    p = result["page_reachable"]
    brk = result["global_break"]
    in_pnot_g = result["in_page_not_global"]

    healthy = g == total and brk is None and p == total and in_pnot_g == 0
    status = "OK" if healthy else "BROKEN"

    print(f"\nRevision {rev_id}  [{status}]")
    print(f"  Total associations : {total}")
    print(f"  Global chain reach : {g} / {total}", end="")
    if brk:
        print(f"  ← breaks here: {brk}", end="")
    print()
    print(f"  Page-local reach   : {p} / {total}  ({result['num_pages']} pages)")

    if in_pnot_g:
        print(f"  Reachable via page but NOT global chain: {in_pnot_g} line(s)")
    if result["in_global_not_page"]:
        print(
            f"  Reachable via global but NOT any page: {result['in_global_not_page']} line(s)"
        )

    if result["page_anomalies"] and verbose:
        print("  Pages with incomplete page-walk:")
        for page, info in sorted(result["page_anomalies"].items()):
            print(f"    page {page}: walked {info['reached']} / {info['total']} lines")


# ---------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------


def repair_revision(
    conn: sqlite3.Connection, revision_id: int, dry_run: bool = True
) -> dict:
    """Rebuild linked list pointers for one revision using page-local ordering.

    Algorithm:
      1. Walk each page using bridge detection (mirrors GET endpoint).
      2. Concatenate pages in sorted order to build the correct global sequence.
      3. Compute expected next_line_id / previous_line_id for every line.
      4. Diff against current DB values; collect lines that need updating.
      5. Find true orphans (in revision but not in any page-local walk).
      6. In non-dry-run mode: apply all updates and delete orphans in one transaction.

    :returns: Summary dict with counts of changes made (or that would be made).
    """
    page_ordered = _page_walk(conn, revision_id)

    # Build global order
    global_order: list[int] = []
    for page in sorted(page_ordered.keys()):
        global_order.extend(page_ordered[page])

    # Expected pointers for every line in the repaired chain
    expected: dict[int, tuple[int | None, int | None]] = {}
    for i, line_id in enumerate(global_order):
        expected[line_id] = (
            global_order[i + 1] if i + 1 < len(global_order) else None,  # next
            global_order[i - 1] if i > 0 else None,  # prev
        )

    # Current state from DB
    current_rows = conn.execute(
        "SELECT line_id, next_line_id, previous_line_id "
        "FROM script_line_revision_association WHERE revision_id = ?",
        (revision_id,),
    ).fetchall()
    current_by_id = {
        r["line_id"]: (r["next_line_id"], r["previous_line_id"]) for r in current_rows
    }

    # Lines needing pointer correction
    updates: list[tuple] = []  # (new_next, new_prev, revision_id, line_id)
    for line_id, (exp_next, exp_prev) in expected.items():
        curr_next, curr_prev = current_by_id.get(line_id, (None, None))
        if curr_next != exp_next or curr_prev != exp_prev:
            updates.append((exp_next, exp_prev, revision_id, line_id))

    # True orphans: in the revision but not reached by any page-local walk
    reachable_set = set(global_order)
    orphan_ids = set(current_by_id.keys()) - reachable_set

    result = {
        "revision_id": revision_id,
        "total": len(current_by_id),
        "pointer_updates": len(updates),
        "orphans_deleted": len(orphan_ids),
        "applied": False,
    }

    if dry_run:
        return result

    # Apply changes inside a single transaction
    try:
        # 1. Delete cue associations for orphaned lines
        for orphan_id in orphan_ids:
            conn.execute(
                "DELETE FROM script_cue_association "
                "WHERE revision_id = ? AND line_id = ?",
                (revision_id, orphan_id),
            )
        # 2. Delete the orphaned associations themselves
        for orphan_id in orphan_ids:
            conn.execute(
                "DELETE FROM script_line_revision_association "
                "WHERE revision_id = ? AND line_id = ?",
                (revision_id, orphan_id),
            )
        # 3. Apply pointer corrections
        for new_next, new_prev, rev_id, line_id in updates:
            conn.execute(
                "UPDATE script_line_revision_association "
                "SET next_line_id = ?, previous_line_id = ? "
                "WHERE revision_id = ? AND line_id = ?",
                (new_next, new_prev, rev_id, line_id),
            )
        conn.commit()
        result["applied"] = True
    except Exception:
        conn.rollback()
        raise

    return result


def print_repair_report(result: dict, dry_run: bool) -> None:
    rev_id = result["revision_id"]
    mode = "DRY RUN" if dry_run else "APPLIED"
    print(f"\nRevision {rev_id}  [{mode}]")
    print(f"  Pointer updates : {result['pointer_updates']}")
    print(f"  Orphans deleted : {result['orphans_deleted']}")
    if not dry_run:
        print(f"  Applied         : {result['applied']}")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose and optionally repair ScriptLineRevisionAssociation "
            "linked list integrity."
        )
    )
    parser.add_argument(
        "--db-path",
        help="Path to the SQLite database. Defaults to reading conf/digiscript.json.",
    )
    parser.add_argument(
        "--revision-id",
        type=int,
        default=None,
        help="Operate on a single revision ID. Default: all revisions.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show per-page breakdown for pages with incomplete walks.",
    )
    parser.add_argument(
        "--repair",
        action="store_true",
        help=(
            "Rebuild chain pointers using page-local ordering. "
            "Runs as a dry run unless --no-dry-run is also passed."
        ),
    )
    parser.add_argument(
        "--no-dry-run",
        dest="dry_run",
        action="store_false",
        default=True,
        help="Actually write changes to the database (use with --repair).",
    )
    args = parser.parse_args()

    db_path = _get_db_path(args)
    print(f"Database: {db_path}")

    conn = _open_db(db_path)
    revision_ids = _get_revision_ids(conn, args.revision_id)

    if not revision_ids:
        print("No revisions found.")
        return

    if args.repair:
        dry_run = args.dry_run
        mode_label = "DRY RUN" if dry_run else "APPLYING CHANGES"
        print(f"\n{'=' * 60}")
        print(f"Repair mode: {mode_label}")
        if not dry_run:
            print("WARNING: This will modify the database. Make a backup first.")
        print(f"{'=' * 60}")

        for rev_id in revision_ids:
            result = repair_revision(conn, rev_id, dry_run=dry_run)
            print_repair_report(result, dry_run=dry_run)

        print(f"\n{'=' * 60}")
        if dry_run:
            print("Re-run with --repair --no-dry-run to apply changes.")
        else:
            print("Repair complete. Re-run without --repair to verify chain integrity.")
    else:
        results = []
        for rev_id in revision_ids:
            result = diagnose_revision(conn, rev_id, verbose=args.verbose)
            results.append(result)
            print_report(result, verbose=args.verbose)

        broken = [r for r in results if r["global_reachable"] != r["total_assocs"]]
        print(f"\n{'=' * 60}")
        print(
            f"Summary: {len(broken)} / {len(results)} revision(s) have chain integrity issues."
        )
        if broken:
            print("Run with --repair to preview chain repairs (dry run by default).")

    conn.close()


if __name__ == "__main__":
    main()
