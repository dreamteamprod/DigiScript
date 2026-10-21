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
    name = next(f for f in os.listdir(VERSIONS_DIR) if f.startswith("d91e929f2e32"))
    spec = importlib.util.spec_from_file_location(
        "persist_revoked_tokens", os.path.join(VERSIONS_DIR, name)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestPersistRevokedTokensMigration(TestCase):
    def test_upgrade_creates_table_and_leaves_api_tokens_untouched(self):
        module = _load_migration()
        with tempfile.TemporaryDirectory() as tmp:
            engine = sa.create_engine(f"sqlite:///{os.path.join(tmp, 'db.sqlite')}")
            with engine.begin() as conn:
                conn.execute(
                    sa.text(
                        "CREATE TABLE user (id INTEGER PRIMARY KEY, api_token TEXT)"
                    )
                )
                conn.execute(
                    sa.text(
                        "INSERT INTO user (id, api_token) VALUES (1, '$2b$12$abc'), (2, NULL)"
                    )
                )
                with Operations.context(MigrationContext.configure(conn)):
                    module.upgrade()
                tokens = conn.execute(
                    sa.text("SELECT api_token FROM user ORDER BY id")
                ).all()
                self.assertEqual([("$2b$12$abc",), (None,)], [tuple(r) for r in tokens])
                self.assertIn("revoked_token", sa.inspect(conn).get_table_names())
            engine.dispose()

    def test_downgrade_drops_table(self):
        module = _load_migration()
        with tempfile.TemporaryDirectory() as tmp:
            engine = sa.create_engine(f"sqlite:///{os.path.join(tmp, 'db.sqlite')}")
            with engine.begin() as conn:
                with Operations.context(MigrationContext.configure(conn)):
                    module.upgrade()
                    module.downgrade()
                self.assertNotIn("revoked_token", sa.inspect(conn).get_table_names())
            engine.dispose()
