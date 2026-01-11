import os
import tempfile

import tornado.escape
from sqlalchemy import select
from tornado.httpclient import HTTPRequest
from tornado.testing import gen_test

from models.script import CompiledScript, Script, ScriptRevision
from models.show import Show, ShowScriptType
from models.user import User
from rbac.role import Role
from test.conftest import DigiScriptTestCase


class TestCompiledScriptsGET(DigiScriptTestCase):
    """Test suite for GET /api/v1/show/script/compiled_scripts endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Rev"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id
            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_compiled_scripts_empty(self):
        """Test GET returns empty list when no compiled scripts exist."""
        response = self.fetch("/api/v1/show/script/compiled_scripts")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual({"scripts": []}, response_body)

    @gen_test
    async def test_get_compiled_scripts_with_data(self):
        """Test GET returns compiled scripts for current show."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Compile the revision
            await CompiledScript.compile_script(self._app, self.revision_id)

            # Fetch compiled scripts
            response = await self.http_client.fetch(
                self.get_url("/api/v1/show/script/compiled_scripts")
            )
            self.assertEqual(200, response.code)
            response_body = tornado.escape.json_decode(response.body)

            # Verify response structure
            self.assertIn("scripts", response_body)
            self.assertEqual(1, len(response_body["scripts"]))
            script = response_body["scripts"][0]
            self.assertEqual(self.revision_id, script["revision_id"])
            self.assertIn("created_at", script)
            self.assertIn("updated_at", script)
            self.assertIn("data_path", script)

            # Verify in database
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, self.revision_id)
                self.assertIsNotNone(compiled)

    @gen_test
    async def test_get_compiled_scripts_isolation(self):
        """Test GET only returns scripts for current show, not other shows."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Create second show with script and revision
            with self._app.get_db().sessionmaker() as session:
                show2 = Show(name="Second Show", script_mode=ShowScriptType.FULL)
                session.add(show2)
                session.flush()

                script2 = Script(show_id=show2.id)
                session.add(script2)
                session.flush()

                revision2 = ScriptRevision(
                    script_id=script2.id, revision=1, description="Second Rev"
                )
                session.add(revision2)
                session.flush()
                revision2_id = revision2.id
                script2.current_revision = revision2.id
                session.commit()

            # Compile both revisions
            await CompiledScript.compile_script(self._app, self.revision_id)
            await CompiledScript.compile_script(self._app, revision2_id)

            # Set current show to first show
            self._app.digi_settings.settings["current_show"].set_value(self.show_id)

            # Fetch compiled scripts
            response = await self.http_client.fetch(
                self.get_url("/api/v1/show/script/compiled_scripts")
            )
            self.assertEqual(200, response.code)
            response_body = tornado.escape.json_decode(response.body)

            # Should only return script from first show
            self.assertEqual(1, len(response_body["scripts"]))
            self.assertEqual(
                self.revision_id, response_body["scripts"][0]["revision_id"]
            )

    def test_get_compiled_scripts_show_not_found(self):
        """Test GET returns 400 when show doesn't exist."""
        # Set current show to non-existent ID
        self._app.digi_settings.settings["current_show"].set_value(99999)

        response = self.fetch("/api/v1/show/script/compiled_scripts")
        self.assertEqual(400, response.code)


class TestCompiledScriptsPOST(DigiScriptTestCase):
    """Test suite for POST /api/v1/show/script/compiled_scripts endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            user = User(username="admin", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Rev"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id
            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    @gen_test
    async def test_post_compile_script_success(self):
        """Test POST successfully compiles a script revision."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({"revision_id": self.revision_id}),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request)

            self.assertEqual(200, response.code)
            response_body = tornado.escape.json_decode(response.body)
            self.assertEqual({}, response_body)

            # Verify database entry created
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, self.revision_id)
                self.assertIsNotNone(compiled)
                self.assertIsNotNone(compiled.data_path)
                self.assertIsNotNone(compiled.created_at)
                self.assertIsNotNone(compiled.updated_at)

                # Verify file exists
                self.assertTrue(os.path.exists(compiled.data_path))

    @gen_test
    async def test_post_compile_script_missing_revision_id(self):
        """Test POST returns 400 when revision_id is missing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({}),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request, raise_error=False)

            self.assertEqual(400, response.code)
            response_body = tornado.escape.json_decode(response.body)
            self.assertEqual("400 revision_id is required", response_body["message"])

            # Verify no database entry created
            with self._app.get_db().sessionmaker() as session:
                all_compiled = session.scalars(select(CompiledScript)).all()
                self.assertEqual(0, len(all_compiled))

    @gen_test
    async def test_post_compile_script_revision_not_found(self):
        """Test POST returns 404 when revision doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({"revision_id": 99999}),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request, raise_error=False)

            self.assertEqual(404, response.code)
            response_body = tornado.escape.json_decode(response.body)
            self.assertEqual("404 script revision not found", response_body["message"])

    @gen_test
    async def test_post_compile_script_revision_wrong_show(self):
        """Test POST returns 404 when revision belongs to different show."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Create second show with script and revision
            with self._app.get_db().sessionmaker() as session:
                show2 = Show(name="Second Show", script_mode=ShowScriptType.FULL)
                session.add(show2)
                session.flush()

                script2 = Script(show_id=show2.id)
                session.add(script2)
                session.flush()

                revision2 = ScriptRevision(
                    script_id=script2.id, revision=1, description="Second Rev"
                )
                session.add(revision2)
                session.flush()
                revision2_id = revision2.id
                script2.current_revision = revision2.id
                session.commit()

            # Try to compile revision from different show
            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({"revision_id": revision2_id}),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request, raise_error=False)

            self.assertEqual(404, response.code)
            response_body = tornado.escape.json_decode(response.body)
            self.assertEqual("404 script revision not found", response_body["message"])

    @gen_test
    async def test_post_compile_script_requires_write_permission(self):
        """Test POST requires WRITE permission on the show."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Create non-admin user with READ-only permission
            with self._app.get_db().sessionmaker() as session:
                readonly_user = User(
                    username="readonly", password="test", is_admin=False
                )
                session.add(readonly_user)
                session.flush()
                readonly_user_id = readonly_user.id
                session.commit()

            # Give READ permission only
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, readonly_user_id)
                show = session.get(Show, self.show_id)
                self._app.rbac.give_role(user, show, Role.READ)

            readonly_token = self._app.jwt_service.create_access_token(
                data={"user_id": readonly_user_id}
            )

            # Try to compile with read-only user
            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({"revision_id": self.revision_id}),
                headers={"Authorization": f"Bearer {readonly_token}"},
            )
            response = await self.http_client.fetch(request, raise_error=False)

            self.assertEqual(403, response.code)

    @gen_test
    async def test_post_compile_script_updates_existing(self):
        """Test POST re-compilation updates existing entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Compile once
            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({"revision_id": self.revision_id}),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request)
            self.assertEqual(200, response.code)

            # Get initial timestamps
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, self.revision_id)
                initial_created_at = compiled.created_at
                initial_updated_at = compiled.updated_at

            # Compile again
            response = await self.http_client.fetch(request)
            self.assertEqual(200, response.code)

            # Verify only one entry exists
            with self._app.get_db().sessionmaker() as session:
                all_compiled = session.scalars(
                    select(CompiledScript).where(
                        CompiledScript.revision_id == self.revision_id
                    )
                ).all()
                self.assertEqual(1, len(all_compiled), "Should have exactly 1 entry")

                # Verify updated_at changed
                compiled = session.get(CompiledScript, self.revision_id)
                self.assertEqual(initial_created_at, compiled.created_at)
                self.assertGreaterEqual(compiled.updated_at, initial_updated_at)

    @gen_test
    async def test_post_compile_script_show_not_found(self):
        """Test POST returns 400 when show doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Set current show to non-existent ID
            self._app.digi_settings.settings["current_show"].set_value(99999)

            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({"revision_id": self.revision_id}),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request, raise_error=False)

            self.assertEqual(400, response.code)


class TestCompiledScriptsDELETE(DigiScriptTestCase):
    """Test suite for DELETE /api/v1/show/script/compiled_scripts endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            user = User(username="admin", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Rev"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id
            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    @gen_test
    async def test_delete_compiled_script_success(self):
        """Test DELETE successfully removes compiled script."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Compile script first
            await CompiledScript.compile_script(self._app, self.revision_id)

            # Get file path for verification
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, self.revision_id)
                file_path = compiled.data_path

            # Delete compiled script
            request = HTTPRequest(
                self.get_url(
                    f"/api/v1/show/script/compiled_scripts?revision_id={self.revision_id}"
                ),
                method="DELETE",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request)

            self.assertEqual(200, response.code)
            response_body = tornado.escape.json_decode(response.body)
            self.assertEqual({}, response_body)

            # Verify database entry deleted
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, self.revision_id)
                self.assertIsNone(compiled, "CompiledScript entry should be deleted")

            # Verify file deleted
            self.assertFalse(os.path.exists(file_path))

    @gen_test
    async def test_delete_compiled_script_missing_revision_id(self):
        """Test DELETE returns 400 when revision_id not provided."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/script/compiled_scripts"),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)

        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("400 revision_id is required", response_body["message"])

    @gen_test
    async def test_delete_compiled_script_invalid_revision_id(self):
        """Test DELETE returns 400 when revision_id is not an integer."""
        request = HTTPRequest(
            self.get_url(
                "/api/v1/show/script/compiled_scripts?revision_id=not_an_integer"
            ),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)

        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("400 revision_id must be an integer", response_body["message"])

    @gen_test
    async def test_delete_compiled_script_not_found(self):
        """Test DELETE returns 404 when compiled script doesn't exist."""
        request = HTTPRequest(
            self.get_url(
                f"/api/v1/show/script/compiled_scripts?revision_id={self.revision_id}"
            ),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)

        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("404 compiled script not found", response_body["message"])

    @gen_test
    async def test_delete_compiled_script_revision_not_found(self):
        """Test DELETE returns 404 when revision doesn't exist."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/script/compiled_scripts?revision_id=99999"),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)

        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("404 script revision not found", response_body["message"])

    @gen_test
    async def test_delete_compiled_script_wrong_show(self):
        """Test DELETE returns 404 when revision belongs to different show."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Create second show with compiled script
            with self._app.get_db().sessionmaker() as session:
                show2 = Show(name="Second Show", script_mode=ShowScriptType.FULL)
                session.add(show2)
                session.flush()

                script2 = Script(show_id=show2.id)
                session.add(script2)
                session.flush()

                revision2 = ScriptRevision(
                    script_id=script2.id, revision=1, description="Second Rev"
                )
                session.add(revision2)
                session.flush()
                revision2_id = revision2.id
                script2.current_revision = revision2.id
                session.commit()

            # Compile revision from second show
            await CompiledScript.compile_script(self._app, revision2_id)

            # Try to delete from first show context
            request = HTTPRequest(
                self.get_url(
                    f"/api/v1/show/script/compiled_scripts?revision_id={revision2_id}"
                ),
                method="DELETE",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request, raise_error=False)

            self.assertEqual(404, response.code)
            response_body = tornado.escape.json_decode(response.body)
            self.assertEqual("404 script revision not found", response_body["message"])

    @gen_test
    async def test_delete_compiled_script_requires_write_permission(self):
        """Test DELETE requires WRITE permission on the show."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Compile script first
            await CompiledScript.compile_script(self._app, self.revision_id)

            # Create non-admin user with READ-only permission
            with self._app.get_db().sessionmaker() as session:
                readonly_user = User(
                    username="readonly", password="test", is_admin=False
                )
                session.add(readonly_user)
                session.flush()
                readonly_user_id = readonly_user.id
                session.commit()

            # Give READ permission only
            with self._app.get_db().sessionmaker() as session:
                user = session.get(User, readonly_user_id)
                show = session.get(Show, self.show_id)
                self._app.rbac.give_role(user, show, Role.READ)

            readonly_token = self._app.jwt_service.create_access_token(
                data={"user_id": readonly_user_id}
            )

            # Try to delete with read-only user
            request = HTTPRequest(
                self.get_url(
                    f"/api/v1/show/script/compiled_scripts?revision_id={self.revision_id}"
                ),
                method="DELETE",
                headers={"Authorization": f"Bearer {readonly_token}"},
            )
            response = await self.http_client.fetch(request, raise_error=False)

            self.assertEqual(403, response.code)

    @gen_test
    async def test_delete_compiled_script_file_missing_but_db_deleted(self):
        """Test DELETE succeeds even when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Compile script first
            await CompiledScript.compile_script(self._app, self.revision_id)

            # Manually delete the file
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, self.revision_id)
                file_path = compiled.data_path
                os.remove(file_path)

            # Verify file is gone
            self.assertFalse(os.path.exists(file_path))

            # Delete compiled script (should succeed despite missing file)
            request = HTTPRequest(
                self.get_url(
                    f"/api/v1/show/script/compiled_scripts?revision_id={self.revision_id}"
                ),
                method="DELETE",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request)

            self.assertEqual(200, response.code)

            # Verify database entry deleted
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, self.revision_id)
                self.assertIsNone(compiled, "DB entry should still be deleted")

    @gen_test
    async def test_delete_compiled_script_show_not_found(self):
        """Test DELETE returns 400 when show doesn't exist."""
        # Set current show to non-existent ID
        self._app.digi_settings.settings["current_show"].set_value(99999)

        request = HTTPRequest(
            self.get_url(
                f"/api/v1/show/script/compiled_scripts?revision_id={self.revision_id}"
            ),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)

        self.assertEqual(400, response.code)


class TestCompiledScriptsIntegration(DigiScriptTestCase):
    """Integration tests for compiled scripts workflow."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            user = User(username="admin", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            # Create two revisions
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="First Rev"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id

            revision2 = ScriptRevision(
                script_id=script.id,
                revision=2,
                description="Second Rev",
                previous_revision_id=revision1.id,
            )
            session.add(revision2)
            session.flush()
            self.revision2_id = revision2.id

            script.current_revision = revision1.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    @gen_test
    async def test_compile_list_delete_workflow(self):
        """Test complete lifecycle: list, compile, list, delete, list."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # 1. GET: Verify empty list
            response = await self.http_client.fetch(
                self.get_url("/api/v1/show/script/compiled_scripts")
            )
            self.assertEqual(200, response.code)
            body = tornado.escape.json_decode(response.body)
            self.assertEqual(0, len(body["scripts"]))

            # 2. POST: Compile revision 1
            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({"revision_id": self.revision1_id}),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request)
            self.assertEqual(200, response.code)

            # 3. GET: Verify 1 compiled script
            response = await self.http_client.fetch(
                self.get_url("/api/v1/show/script/compiled_scripts")
            )
            self.assertEqual(200, response.code)
            body = tornado.escape.json_decode(response.body)
            self.assertEqual(1, len(body["scripts"]))
            self.assertEqual(self.revision1_id, body["scripts"][0]["revision_id"])

            # 4. POST: Compile revision 2
            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({"revision_id": self.revision2_id}),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request)
            self.assertEqual(200, response.code)

            # 5. GET: Verify 2 compiled scripts
            response = await self.http_client.fetch(
                self.get_url("/api/v1/show/script/compiled_scripts")
            )
            self.assertEqual(200, response.code)
            body = tornado.escape.json_decode(response.body)
            self.assertEqual(2, len(body["scripts"]))

            # 6. DELETE: Remove revision 1 compilation
            request = HTTPRequest(
                self.get_url(
                    f"/api/v1/show/script/compiled_scripts?revision_id={self.revision1_id}"
                ),
                method="DELETE",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request)
            self.assertEqual(200, response.code)

            # 7. GET: Verify 1 compiled script remains
            response = await self.http_client.fetch(
                self.get_url("/api/v1/show/script/compiled_scripts")
            )
            self.assertEqual(200, response.code)
            body = tornado.escape.json_decode(response.body)
            self.assertEqual(1, len(body["scripts"]))
            self.assertEqual(self.revision2_id, body["scripts"][0]["revision_id"])

            # 8. DELETE: Remove revision 2 compilation
            request = HTTPRequest(
                self.get_url(
                    f"/api/v1/show/script/compiled_scripts?revision_id={self.revision2_id}"
                ),
                method="DELETE",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request)
            self.assertEqual(200, response.code)

            # 9. GET: Verify empty list
            response = await self.http_client.fetch(
                self.get_url("/api/v1/show/script/compiled_scripts")
            )
            self.assertEqual(200, response.code)
            body = tornado.escape.json_decode(response.body)
            self.assertEqual(0, len(body["scripts"]))

    @gen_test
    async def test_recompilation_updates_file(self):
        """Test that recompilation updates the existing entry."""
        with tempfile.TemporaryDirectory() as temp_dir:
            await self._app.digi_settings.set("compiled_script_path", temp_dir)

            # Compile once
            request = HTTPRequest(
                self.get_url("/api/v1/show/script/compiled_scripts"),
                method="POST",
                body=tornado.escape.json_encode({"revision_id": self.revision1_id}),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            response = await self.http_client.fetch(request)
            self.assertEqual(200, response.code)

            # Get initial state
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, self.revision1_id)
                initial_updated_at = compiled.updated_at
                initial_path = compiled.data_path

            # Recompile
            response = await self.http_client.fetch(request)
            self.assertEqual(200, response.code)

            # Verify update
            with self._app.get_db().sessionmaker() as session:
                compiled = session.get(CompiledScript, self.revision1_id)
                self.assertGreaterEqual(compiled.updated_at, initial_updated_at)
                # File path should be the same
                self.assertEqual(initial_path, compiled.data_path)
                # File should still exist
                self.assertTrue(os.path.exists(compiled.data_path))
