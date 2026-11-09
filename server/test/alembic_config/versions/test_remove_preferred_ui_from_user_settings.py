import importlib.util
import os
import tempfile
from unittest import TestCase

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


VERSIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "alembic_config", "versions"
)


def _load_migration():
    name = next(f for f in os.listdir(VERSIONS_DIR) if f.startswith("079ddf32e0c3"))
    spec = importlib.util.spec_from_file_location(
        "remove_preferred_ui_from_user_settings", os.path.join(VERSIONS_DIR, name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_user_settings_table(conn):
    conn.execute(
        sa.text(
            "CREATE TABLE user_settings ("
            "_user_id INTEGER PRIMARY KEY, "
            "console_log_level TEXT, "
            "preferred_ui TEXT, "
            "CONSTRAINT ck_user_settings_preferred_ui "
            "CHECK (preferred_ui IS NULL OR preferred_ui IN ('old', 'new'))"
            ")"
        )
    )
    conn.execute(
        sa.text(
            "INSERT INTO user_settings (_user_id, console_log_level, preferred_ui) "
            "VALUES (1, 'WARN', 'old'), (2, 'INFO', 'new'), (3, 'DEBUG', NULL)"
        )
    )


class TestRemovePreferredUiMigration(TestCase):
    def test_upgrade_drops_column_and_constraint_and_leaves_other_columns_untouched(
        self,
    ):
        module = _load_migration()
        with tempfile.TemporaryDirectory() as tmp:
            engine = sa.create_engine(f"sqlite:///{os.path.join(tmp, 'db.sqlite')}")
            with engine.begin() as conn:
                _create_user_settings_table(conn)
                with Operations.context(MigrationContext.configure(conn)):
                    module.upgrade()

                columns = {
                    col["name"] for col in sa.inspect(conn).get_columns("user_settings")
                }
                self.assertNotIn("preferred_ui", columns)

                constraint_names = {
                    c["name"]
                    for c in sa.inspect(conn).get_check_constraints("user_settings")
                }
                self.assertNotIn("ck_user_settings_preferred_ui", constraint_names)

                rows = conn.execute(
                    sa.text(
                        "SELECT _user_id, console_log_level FROM user_settings "
                        "ORDER BY _user_id"
                    )
                ).all()
                self.assertEqual(
                    [(1, "WARN"), (2, "INFO"), (3, "DEBUG")],
                    [tuple(r) for r in rows],
                )
            engine.dispose()

    def test_downgrade_restores_column_and_constraint(self):
        module = _load_migration()
        with tempfile.TemporaryDirectory() as tmp:
            engine = sa.create_engine(f"sqlite:///{os.path.join(tmp, 'db.sqlite')}")
            with engine.begin() as conn:
                _create_user_settings_table(conn)
                with Operations.context(MigrationContext.configure(conn)):
                    module.upgrade()
                    module.downgrade()

                columns = {
                    col["name"] for col in sa.inspect(conn).get_columns("user_settings")
                }
                self.assertIn("preferred_ui", columns)

                constraint_names = {
                    c["name"]
                    for c in sa.inspect(conn).get_check_constraints("user_settings")
                }
                self.assertIn("ck_user_settings_preferred_ui", constraint_names)

                # downgrade recreates the column empty — restoring prior values isn't
                # possible once dropped, so rows should now have NULL preferred_ui.
                rows = conn.execute(
                    sa.text(
                        "SELECT _user_id, preferred_ui FROM user_settings "
                        "ORDER BY _user_id"
                    )
                ).all()
                self.assertEqual(
                    [(1, None), (2, None), (3, None)],
                    [tuple(r) for r in rows],
                )
            engine.dispose()
