"""Tests for the shared ScriptLineRevisionAssociation repair helpers.

Builds minimal hand-written tables (not the full app schema) so the
page-walk/bridge/orphan logic in ``repair_linked_list_utils`` can be exercised
directly against a real SQLite connection, independent of the ORM.
"""

import os
import tempfile
from contextlib import contextmanager
from unittest import TestCase

import sqlalchemy as sa

from alembic_config.repair_linked_list_utils import repair_revision_max_bridge


@contextmanager
def _connection():
    with tempfile.TemporaryDirectory() as tmp:
        engine = sa.create_engine(f"sqlite:///{os.path.join(tmp, 'db.sqlite')}")
        with engine.begin() as conn:
            conn.execute(
                sa.text("CREATE TABLE script_revisions (id INTEGER PRIMARY KEY)")
            )
            conn.execute(
                sa.text(
                    "CREATE TABLE script_lines (id INTEGER PRIMARY KEY, page INTEGER)"
                )
            )
            conn.execute(
                sa.text(
                    "CREATE TABLE script_line_parts (id INTEGER PRIMARY KEY, line_id INTEGER)"
                )
            )
            conn.execute(
                sa.text(
                    "CREATE TABLE script_line_cuts (line_part_id INTEGER, revision_id INTEGER, "
                    "PRIMARY KEY (line_part_id, revision_id))"
                )
            )
            conn.execute(
                sa.text(
                    "CREATE TABLE script_cue_association (revision_id INTEGER, line_id INTEGER, "
                    "cue_id INTEGER, PRIMARY KEY (revision_id, line_id, cue_id))"
                )
            )
            conn.execute(
                sa.text(
                    "CREATE TABLE script_line_revision_association ("
                    "revision_id INTEGER, line_id INTEGER, next_line_id INTEGER, "
                    "previous_line_id INTEGER, PRIMARY KEY (revision_id, line_id))"
                )
            )
            yield conn
        engine.dispose()


def _seed_revision(conn, revision_id, lines):
    """*lines*: iterable of (line_id, page, next_id, prev_id)."""
    conn.execute(
        sa.text("INSERT INTO script_revisions (id) VALUES (:id)"), {"id": revision_id}
    )
    for line_id, page, next_id, prev_id in lines:
        conn.execute(
            sa.text("INSERT INTO script_lines (id, page) VALUES (:id, :page)"),
            {"id": line_id, "page": page},
        )
        conn.execute(
            sa.text(
                "INSERT INTO script_line_revision_association "
                "(revision_id, line_id, next_line_id, previous_line_id) "
                "VALUES (:rev, :lid, :next, :prev)"
            ),
            {"rev": revision_id, "lid": line_id, "next": next_id, "prev": prev_id},
        )


def _current_line_ids(conn, revision_id):
    return {
        row[0]
        for row in conn.execute(
            sa.text(
                "SELECT line_id FROM script_line_revision_association "
                "WHERE revision_id = :rev"
            ),
            {"rev": revision_id},
        ).fetchall()
    }


class TestRepairRevisionMaxBridge(TestCase):
    def test_noop_on_a_page_emptied_in_the_middle_does_not_delete_real_content(self):
        """Regression: a page with zero lines left (ordinary editing, not
        corruption) must not make the repair treat everything after it as
        unreachable orphans. 1(p1) -> 2(p1) -> 3(p3) -> 4(p3) -> 5(p4), page 2
        has no lines at all."""
        with _connection() as conn:
            _seed_revision(
                conn,
                1,
                [
                    (1, 1, 2, None),
                    (2, 1, 3, 1),
                    (3, 3, 4, 2),
                    (4, 3, 5, 3),
                    (5, 4, None, 4),
                ],
            )
            result = repair_revision_max_bridge(conn, 1)
            self.assertEqual(0, result["orphans_deleted"])
            self.assertEqual(0, result["pointer_updates"])
            self.assertEqual({1, 2, 3, 4, 5}, _current_line_ids(conn, 1))

    def test_duplicate_bridge_candidate_picks_max_and_deletes_the_true_orphan(self):
        """Baseline for the original 897ae2963f6d corruption shape: two lines
        both claim to be the first line of page 2 (the "added" misclassification
        bug) — the higher line_id (the live replacement) must be kept and
        reachable, the lower (abandoned original) must be deleted as a true
        orphan, since nothing's next_line_id points to it either."""
        with _connection() as conn:
            _seed_revision(
                conn,
                1,
                [
                    (1, 1, 3, None),  # page 1, head, points at the *live* page-2 line
                    (2, 2, None, 1),  # abandoned original page-2 line — unreachable
                    (3, 2, 4, 1),  # live page-2 line, chosen by max()
                    (4, 3, None, 3),
                ],
            )
            result = repair_revision_max_bridge(conn, 1)
            self.assertEqual(1, result["orphans_deleted"])
            self.assertEqual(0, result["pointer_updates"])
            self.assertEqual({1, 3, 4}, _current_line_ids(conn, 1))

    def test_non_last_page_append_break_is_fixed_without_deleting_anything(self):
        """This PR's own target bug: line 2's next_line_id was dropped to NULL
        when it should point at line 3 (the next page's first line, whose own
        previous_line_id was never touched). Every line still belongs to a
        real page, so nothing should be deleted — only the one pointer fixed."""
        with _connection() as conn:
            _seed_revision(
                conn,
                1,
                [
                    (1, 1, 2, None),
                    (2, 1, None, 1),  # broken: should point at 3
                    (3, 2, None, 2),
                ],
            )
            result = repair_revision_max_bridge(conn, 1)
            self.assertEqual(0, result["orphans_deleted"])
            self.assertEqual(1, result["pointer_updates"])
            self.assertEqual({1, 2, 3}, _current_line_ids(conn, 1))

            row = conn.execute(
                sa.text(
                    "SELECT next_line_id, previous_line_id "
                    "FROM script_line_revision_association "
                    "WHERE revision_id = 1 AND line_id = 2"
                )
            ).one()
            self.assertEqual((3, 1), tuple(row))

    def test_repair_is_idempotent(self):
        """Running the repair twice must leave the second pass a no-op."""
        with _connection() as conn:
            _seed_revision(
                conn,
                1,
                [
                    (1, 1, 2, None),
                    (2, 1, None, 1),
                    (3, 2, None, 2),
                ],
            )
            first = repair_revision_max_bridge(conn, 1)
            self.assertEqual(1, first["pointer_updates"])

            second = repair_revision_max_bridge(conn, 1)
            self.assertEqual(0, second["pointer_updates"])
            self.assertEqual(0, second["orphans_deleted"])

    def test_orphan_deletion_also_removes_its_line_cuts(self):
        """script_line_cuts is revision-scoped by line_part_id and isn't
        cleaned up by the ORM cascade when a migration deletes rows with raw
        SQL — it must be deleted explicitly, or a later, unrelated line part
        can silently inherit a stale "cut" row once SQLite reuses the freed id
        (script_line_parts.id has no AUTOINCREMENT)."""
        with _connection() as conn:
            _seed_revision(
                conn,
                1,
                [
                    (1, 1, 3, None),
                    (2, 2, None, 1),  # orphan
                    (3, 2, 4, 1),
                    (4, 3, None, 3),
                ],
            )
            conn.execute(
                sa.text("INSERT INTO script_line_parts (id, line_id) VALUES (20, 2)")
            )
            conn.execute(
                sa.text(
                    "INSERT INTO script_line_cuts (line_part_id, revision_id) "
                    "VALUES (20, 1)"
                )
            )

            result = repair_revision_max_bridge(conn, 1)
            self.assertEqual(1, result["orphans_deleted"])

            remaining_cuts = conn.execute(
                sa.text("SELECT COUNT(*) FROM script_line_cuts")
            ).scalar()
            self.assertEqual(0, remaining_cuts)
            remaining_parts = conn.execute(
                sa.text("SELECT COUNT(*) FROM script_line_parts WHERE line_id = 2")
            ).scalar()
            self.assertEqual(0, remaining_parts)
