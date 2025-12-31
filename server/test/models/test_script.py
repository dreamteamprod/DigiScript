import os
import tempfile

from tornado.testing import gen_test
from sqlalchemy import func, select

from models.script import CompiledScript, ScriptRevision, StageDirectionStyle, Script
from models.show import Show, ShowScriptType
from models.user import User, UserOverrides
from test.conftest import DigiScriptTestCase


class TestScriptModels(DigiScriptTestCase):
    def test_stage_direction_style_pre_delete_hook(self):
        """Test that StageDirectionStyle.pre_delete() deletes associated user overrides.

        This tests the query at lines 204-207:
        session.scalars(
            select(UserOverrides).where(
                UserOverrides.settings_type == self.__tablename__
            )
        ).all()

        We create a stage direction style, add user overrides for it, then delete
        the style and verify the overrides are also deleted.
        """
        # Create test data
        with self._app.get_db().sessionmaker() as session:
            # Create show and script
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            # Create stage direction style
            style = StageDirectionStyle(
                script_id=script.id,
                description="Test Style",
                bold=True,
                italic=False,
            )
            session.add(style)
            session.flush()
            style_id = style.id

            # Create user and user overrides for this style
            user = User(username="testuser", password="test")
            session.add(user)
            session.flush()

            override = UserOverrides(
                user_id=user.id,
                settings_type="stage_direction_styles",
                settings='{"bold": false}',
            )
            session.add(override)
            session.commit()

        # Verify override exists
        with self._app.get_db().sessionmaker() as session:
            override_count = session.scalar(
                select(func.count())
                .select_from(UserOverrides)
                .where(UserOverrides.settings_type == "stage_direction_styles")
            )
            self.assertEqual(1, override_count)

        # Delete the style (this should trigger pre_delete hook)
        with self._app.get_db().sessionmaker() as session:
            style = session.get(StageDirectionStyle, style_id)
            session.delete(style)
            session.commit()

        # Verify override was deleted by the hook
        with self._app.get_db().sessionmaker() as session:
            override_count = session.scalar(
                select(func.count())
                .select_from(UserOverrides)
                .where(UserOverrides.settings_type == "stage_direction_styles")
            )
            self.assertEqual(0, override_count, "User override should be deleted")

    @gen_test
    async def test_compile_script_creates_compiled_entry(self):
        """Test that CompiledScript.compile_script() creates a compiled script entry.

        This tests the queries at lines 242-295 in the compile_script method,
        including:
        - Line 244: with_entities for line IDs
        - Line 249: with_entities for max page
        - Line 265: .has() relationship filter
        - Line 290: composite key .get()

        We call the actual compile_script class method and verify it creates
        a CompiledScript entry with the correct data.
        """
        # Setup: Create temporary directory for compiled scripts
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Create test data - we don't need actual script content,
            # just enough structure for the method to run
            with self._app.get_db().sessionmaker() as session:
                show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
                session.add(show)
                session.flush()

                script = Script(show_id=show.id)
                session.add(script)
                session.flush()

                revision = ScriptRevision(
                    script_id=script.id, revision=1, description="Test Revision"
                )
                session.add(revision)
                session.commit()
                revision_id = revision.id

            # Call the actual compile_script method
            await CompiledScript.compile_script(self._app, revision_id)

            # Verify: Check that a CompiledScript entry was created
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, revision_id)
                self.assertIsNotNone(compiled, "CompiledScript entry should be created")
                self.assertEqual(compiled.revision_id, revision_id)
                self.assertIsNotNone(compiled.data_path)
                # Verify the file was created
                self.assertTrue(
                    os.path.exists(compiled.data_path),
                    "Compiled script file should exist",
                )

    def test_load_compiled_script_returns_data(self):
        """Test that CompiledScript.load_compiled_script() returns script data.

        This test verifies the load_compiled_script class method works correctly.
        Note: This method already uses modern syntax (session.get()) so we're
        just ensuring test coverage exists.
        """
        # Setup: Create a revision (compile_script will be called automatically)
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Revision"
            )
            session.add(revision)
            session.commit()
            revision_id = revision.id

        # Call the actual load_compiled_script method
        # (it will trigger compilation if needed)
        result = CompiledScript.load_compiled_script(self._app, revision_id)

        # Verify: Result should be a dict (empty since we have no lines, but should work)
        self.assertIsInstance(result, dict)
