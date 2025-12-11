from test.conftest import DigiScriptTestCase

import tornado.escape
from sqlalchemy import func, select

from models.cue import Cue, CueAssociation, CueType
from models.script import (
    Script,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptRevision,
)
from models.show import Act, Character, Scene, Show


class TestScriptRevisionsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/revisions endpoints."""

    def setUp(self):
        super().setUp()
        # Create base test data
        with self._app.get_db().sessionmaker() as session:
            # Create a test show
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create script
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            # Create first revision
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id

            # Link revision to script
            script.current_revision = revision1.id

            # Create second revision
            revision2 = ScriptRevision(
                script_id=script.id,
                revision=2,
                description="Second",
                previous_revision_id=revision1.id,
            )
            session.add(revision2)
            session.flush()
            self.revision2_id = revision2.id

            session.commit()

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_revisions(self):
        """Test GET /api/v1/show/script/revisions.

        This tests the query at line 36:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/script/revisions")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(self.revision1_id, response_body["current_revision"])
        self.assertEqual(2, len(response_body["revisions"]))

    def test_get_revisions_no_script(self):
        """Test GET /api/v1/show/script/revisions returns 404 when no script exists."""
        # Create a show with no script
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Empty Show")
            session.add(show2)
            session.commit()
            empty_show_id = show2.id

        self._app.digi_settings.settings["current_show"].set_value(empty_show_id)

        response = self.fetch("/api/v1/show/script/revisions")
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("404 script not found", response_body["message"])


class TestScriptCurrentRevisionController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/revisions/current endpoints."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_current_revision(self):
        """Test GET /api/v1/show/script/revisions/current.

        This tests the query at line 255:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/script/revisions/current")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(self.revision_id, response_body["current_revision"])

    def test_get_current_revision_no_script(self):
        """Test GET returns 404 when no script exists."""
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Empty Show")
            session.add(show2)
            session.commit()
            empty_show_id = show2.id

        self._app.digi_settings.settings["current_show"].set_value(empty_show_id)

        response = self.fetch("/api/v1/show/script/revisions/current")
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("404 script not found", response_body["message"])


class TestScriptRevisionCreate(DigiScriptTestCase):
    """Test POST /api/v1/show/script/revisions endpoint.

    This tests the func.max() query at lines 89-93 in controllers/api/show/script/revisions.py:
    session.scalar(
        select(func.max(ScriptRevision.revision))
        .where(ScriptRevision.script_id == script.id)
    )

    The query is used to determine the next revision number when creating a new revision.
    """

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            from models.user import User

            # Create admin user for authentication
            user = User(username="admin", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            # Create show
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create script
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            # Create initial revision
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id
            script.current_revision = revision1.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_create_revision_uses_max_query(self):
        """Test POST /api/v1/show/script/revisions creates revision with correct number.

        When creating a new revision, the endpoint uses func.max() to find the highest
        existing revision number and increments it. This test verifies that behavior.
        """
        # Create a JWT token for authentication
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Create a new revision - this triggers the max query
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode({"description": "Second revision"}),
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify the revision was created
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        new_revision_id = response_body["id"]

        # Verify the new revision has the correct number (2)
        with self._app.get_db().sessionmaker() as session:
            new_rev = session.get(ScriptRevision, new_revision_id)
            self.assertEqual(2, new_rev.revision)


class TestScriptRevisionDelete(DigiScriptTestCase):
    """Test DELETE /api/v1/show/script/revisions endpoint.

    This tests the "find revision 1" query at lines 206-213 in controllers/api/show/script/revisions.py:
    session.scalars(
        select(ScriptRevision)
        .where(ScriptRevision.script_id == script.id, ScriptRevision.revision == 1)
    ).one()

    The query is used as a fallback when deleting the current revision and it has no previous_revision_id.
    """

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            from models.user import User

            # Create admin user for authentication
            user = User(username="admin", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            # Create show
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create script
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            # Create revision 1
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id

            # Create revision 2 WITHOUT previous_revision_id (unusual case)
            # This forces the fallback query when we delete it
            revision2 = ScriptRevision(
                script_id=script.id,
                revision=2,
                description="Second",
                previous_revision_id=None,  # No link to previous!
            )
            session.add(revision2)
            session.flush()
            self.revision2_id = revision2.id

            # Make revision 2 current
            script.current_revision = revision2.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_delete_revision_uses_find_first_query(self):
        """Test DELETE /api/v1/show/script/revisions falls back to revision 1.

        When deleting the current revision that has no previous_revision_id,
        the endpoint uses a query to find revision 1 as a fallback.
        """
        # Create a JWT token for authentication
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Delete revision 2 - this triggers the "find revision 1" fallback query
        response = self.fetch(
            f"/api/v1/show/script/revisions?rev_id={self.revision2_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify the deletion succeeded
        self.assertEqual(200, response.code)

        # Verify the script now points to revision 1 (the fallback)
        with self._app.get_db().sessionmaker() as session:
            script = session.get(Script, self.script_id)
            self.assertEqual(self.revision1_id, script.current_revision)


class TestRevisionDeletionWithLines(DigiScriptTestCase):
    """Test deleting revisions with script lines (Issue #670).

    When deleting a revision, the post_delete hook in ScriptLineRevisionAssociation
    must properly clean up orphaned lines without triggering FK constraint errors.
    This tests the fix that uses session.no_autoflush to prevent lazy loading from
    triggering premature autoflush during cascade deletion.
    """

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            from models.user import User

            user = User(username="admin", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id
            script.current_revision = revision1.id

            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()
            self.act_id = act.id

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            self.scene_id = scene.id

            character = Character(show_id=show.id, name="Test Character")
            session.add(character)
            session.flush()
            self.character_id = character.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def test_delete_revision_with_multiple_lines(self):
        """Test deleting a revision that has multiple script lines.

        This test creates a revision with 5 lines (with next/previous pointers),
        then creates a second revision via the API (which copies the lines),
        then deletes the second revision. This should succeed without FK errors.
        """
        # Create lines in revision 1 via API
        initial_lines = [
            {
                "id": None,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "stage_direction": False,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": f"Line {i}",
                    }
                ],
                "stage_direction_style_id": None,
            }
            for i in range(1, 6)
        ]

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(initial_lines),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Create revision 2 via API (copies all lines from revision 1)
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode({"description": "Second revision"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        revision2_id = response_body["id"]

        # Now delete revision 2
        response = self.fetch(
            f"/api/v1/show/script/revisions?rev_id={revision2_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        # Should succeed without FK constraint error
        self.assertEqual(200, response.code)

        # Verify complete cascade deletion
        with self._app.get_db().sessionmaker() as session:
            # 1. Revision should be deleted
            deleted_rev = session.get(ScriptRevision, revision2_id)
            self.assertIsNone(deleted_rev)

            # 2. ScriptLineRevisionAssociation records for revision 2 should be deleted
            rev2_assocs = session.scalars(
                select(ScriptLineRevisionAssociation).where(
                    ScriptLineRevisionAssociation.revision_id == revision2_id
                )
            ).all()
            self.assertEqual(
                0,
                len(rev2_assocs),
                "All associations for revision 2 should be deleted",
            )

            # 3. Verify revision 1 still has its associations (shared lines should still exist)
            rev1_assocs = session.scalars(
                select(ScriptLineRevisionAssociation).where(
                    ScriptLineRevisionAssociation.revision_id == self.revision1_id
                )
            ).all()
            self.assertEqual(
                5, len(rev1_assocs), "Revision 1 associations should still exist"
            )

            # 4. ScriptLine objects should still exist (shared with revision 1)
            # Note: When creating revision 2, lines are SHARED (same line_id), not duplicated
            lines = session.scalars(select(ScriptLine)).all()
            self.assertEqual(
                5, len(lines), "Lines should still exist (shared with revision 1)"
            )

    def test_delete_non_current_revision(self):
        """Test deleting a non-current revision with lines.

        This ensures the deletion works even when deleting an old revision
        while a newer one is current.
        """
        # Create lines in revision 1
        initial_lines = [
            {
                "id": None,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "stage_direction": False,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": "Line 1",
                    }
                ],
                "stage_direction_style_id": None,
            }
        ]

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(initial_lines),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Create revision 2
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode({"description": "Second"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        revision2_id = tornado.escape.json_decode(response.body)["id"]

        # Create revision 3 (now current)
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode({"description": "Third"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Delete revision 2 (non-current)
        response = self.fetch(
            f"/api/v1/show/script/revisions?rev_id={revision2_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code)

        # Verify complete cascade deletion
        with self._app.get_db().sessionmaker() as session:
            # 1. Revision 2 should be deleted
            deleted_rev = session.get(ScriptRevision, revision2_id)
            self.assertIsNone(deleted_rev)

            # 2. ScriptLineRevisionAssociation records for revision 2 should be deleted
            rev2_assocs = session.scalars(
                select(ScriptLineRevisionAssociation).where(
                    ScriptLineRevisionAssociation.revision_id == revision2_id
                )
            ).all()
            self.assertEqual(
                0,
                len(rev2_assocs),
                "All associations for revision 2 should be deleted",
            )

            # 3. Verify other revisions still have their associations
            all_assocs = session.scalars(select(ScriptLineRevisionAssociation)).all()
            self.assertGreater(
                len(all_assocs),
                0,
                "Associations for other revisions should still exist",
            )

    def test_delete_revision_with_cues(self):
        """Test deleting a revision that has cues attached to lines.

        This ensures the CueAssociation.post_delete hook properly handles
        cascade deletion without triggering FK constraint errors.
        """
        # Create lines in revision 1
        initial_lines = [
            {
                "id": None,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "stage_direction": False,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": "Line 1",
                    }
                ],
                "stage_direction_style_id": None,
            }
        ]

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(initial_lines),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Create a cue type
        with self._app.get_db().sessionmaker() as session:
            cue_type = CueType(
                show_id=self.show_id,
                prefix="LX",
                description="Lighting",
                colour="#FF0000",
            )
            session.add(cue_type)
            session.flush()
            cue_type_id = cue_type.id
            session.commit()

        # Create a cue
        with self._app.get_db().sessionmaker() as session:
            cue = Cue(cue_type_id=cue_type_id, ident="1")
            session.add(cue)
            session.flush()
            cue_id = cue.id

            # Get the line we just created
            line = session.scalars(
                select(ScriptLine).where(ScriptLine.page == 1)
            ).first()
            line_id = line.id

            # Create cue association
            cue_assoc = CueAssociation(
                revision_id=self.revision1_id, line_id=line_id, cue_id=cue_id
            )
            session.add(cue_assoc)
            session.commit()

        # Create revision 2 (copies lines and cue associations)
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode({"description": "Second"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        revision2_id = tornado.escape.json_decode(response.body)["id"]

        # Delete revision 2 (should not cause FK constraint error)
        response = self.fetch(
            f"/api/v1/show/script/revisions?rev_id={revision2_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        # Should succeed without FK constraint error
        self.assertEqual(200, response.code)

        # Verify complete cascade deletion
        with self._app.get_db().sessionmaker() as session:
            # 1. Revision should be deleted
            deleted_rev = session.get(ScriptRevision, revision2_id)
            self.assertIsNone(deleted_rev)

            # 2. CueAssociation for revision 2 should be deleted
            rev2_cue_assocs = session.scalars(
                select(CueAssociation).where(CueAssociation.revision_id == revision2_id)
            ).all()
            self.assertEqual(
                0,
                len(rev2_cue_assocs),
                "Cue associations for revision 2 should be deleted",
            )

            # 3. CueAssociation for revision 1 should still exist
            rev1_cue_assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.revision_id == self.revision1_id
                )
            ).all()
            self.assertEqual(
                1,
                len(rev1_cue_assocs),
                "Cue associations for revision 1 should still exist",
            )

            # 4. Cue object should still exist (shared with revision 1)
            cues = session.scalars(select(Cue)).all()
            self.assertEqual(
                1, len(cues), "Cue should still exist (shared with revision 1)"
            )
