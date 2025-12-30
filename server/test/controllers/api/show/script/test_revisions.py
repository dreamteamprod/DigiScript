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


class TestScriptRevisionBranching(DigiScriptTestCase):
    """Test branching functionality for script revisions (Issue #785).

    Tests the new parent_revision_id and set_as_current parameters that allow
    creating revisions from any node in the revision tree, not just the current revision.
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

            # Create revision 1
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id
            script.current_revision = revision1.id

            # Create revision 2 (child of revision 1)
            revision2 = ScriptRevision(
                script_id=script.id,
                revision=2,
                description="Second",
                previous_revision_id=revision1.id,
            )
            session.add(revision2)
            session.flush()
            self.revision2_id = revision2.id

            # Create revision 3 (child of revision 2, now current)
            revision3 = ScriptRevision(
                script_id=script.id,
                revision=3,
                description="Third",
                previous_revision_id=revision2.id,
            )
            session.add(revision3)
            session.flush()
            self.revision3_id = revision3.id
            script.current_revision = revision3.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def test_create_revision_from_current_revision_default_behavior(self):
        """Test creating a revision without specifying parent (backward compatibility).

        When no parent_revision_id is provided, should default to current revision
        and set_as_current should default to True.
        """
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode({"description": "Fourth revision"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        new_revision_id = response_body["id"]

        with self._app.get_db().sessionmaker() as session:
            new_rev = session.get(ScriptRevision, new_revision_id)
            script = session.get(Script, self.script_id)

            # Should be child of revision 3 (current)
            self.assertEqual(self.revision3_id, new_rev.previous_revision_id)
            self.assertEqual(4, new_rev.revision)
            # Should be set as current
            self.assertEqual(new_revision_id, script.current_revision)

    def test_create_branch_from_non_current_revision(self):
        """Test creating a branch from a non-current revision.

        When parent_revision_id points to a non-current revision and
        set_as_current is False, should create a branch without changing current.
        """
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "description": "Branch from revision 2",
                    "parent_revision_id": self.revision2_id,
                    "set_as_current": False,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        branch_revision_id = response_body["id"]

        with self._app.get_db().sessionmaker() as session:
            branch_rev = session.get(ScriptRevision, branch_revision_id)
            script = session.get(Script, self.script_id)

            # Should be child of revision 2 (not current revision 3)
            self.assertEqual(self.revision2_id, branch_rev.previous_revision_id)
            self.assertEqual(4, branch_rev.revision)
            # Current revision should NOT change
            self.assertEqual(self.revision3_id, script.current_revision)

    def test_create_branch_from_non_current_with_set_as_current_true(self):
        """Test creating a branch from non-current revision and setting it as current.

        When parent_revision_id points to a non-current revision but
        set_as_current is True, should create branch AND set it as current.
        """
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "description": "Branch from revision 1, set as current",
                    "parent_revision_id": self.revision1_id,
                    "set_as_current": True,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        branch_revision_id = response_body["id"]

        with self._app.get_db().sessionmaker() as session:
            branch_rev = session.get(ScriptRevision, branch_revision_id)
            script = session.get(Script, self.script_id)

            # Should be child of revision 1
            self.assertEqual(self.revision1_id, branch_rev.previous_revision_id)
            self.assertEqual(4, branch_rev.revision)
            # Should be set as current
            self.assertEqual(branch_revision_id, script.current_revision)

    def test_invalid_parent_revision_id(self):
        """Test that providing an invalid parent_revision_id returns 404."""
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "description": "Branch from invalid parent",
                    "parent_revision_id": 99999,  # Non-existent ID
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("404 parent revision not found", response_body["message"])

    def test_parent_revision_from_different_script(self):
        """Test that parent_revision_id must belong to the same script."""
        # Create a second show with its own script and revision
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Second Show")
            session.add(show2)
            session.flush()
            show2_id = show2.id

            script2 = Script(show_id=show2.id)
            session.add(script2)
            session.flush()

            revision_other = ScriptRevision(
                script_id=script2.id, revision=1, description="Other script revision"
            )
            session.add(revision_other)
            session.flush()
            other_revision_id = revision_other.id
            script2.current_revision = other_revision_id

            session.commit()

        # Try to create a revision in script 1 with parent from script 2
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "description": "Invalid cross-script branch",
                    "parent_revision_id": other_revision_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(
            "Parent revision belongs to different script", response_body["message"]
        )


class TestScriptRevisionBranchingWithLines(DigiScriptTestCase):
    """Test branching with script lines to ensure associations are copied correctly.

    When branching from a non-current revision, the associations (lines, cues, cuts)
    should be copied from the parent revision, not from the current revision.
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

    def test_branch_copies_associations_from_parent_not_current(self):
        """Test that branching copies associations from parent, not current revision.

        Create revision 1 with 2 lines, then revision 2 with 3 lines (current).
        Branch from revision 1 should copy 2 lines, not 3.
        """
        # Create 2 lines in revision 1
        lines_rev1 = [
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
                        "line_text": f"Rev1 Line {i}",
                    }
                ],
                "stage_direction_style_id": None,
            }
            for i in range(1, 3)
        ]

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(lines_rev1),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Create revision 2 (copies 2 lines from revision 1)
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode({"description": "Second revision"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        revision2_id = tornado.escape.json_decode(response.body)["id"]

        # Add 1 more line to revision 2 (now current has 3 lines)
        lines_rev2_additional = [
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
                        "line_text": "Rev2 Additional Line",
                    }
                ],
                "stage_direction_style_id": None,
            }
        ]

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(lines_rev2_additional),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify revision 2 now has 3 line associations
        with self._app.get_db().sessionmaker() as session:
            rev2_assocs = session.scalars(
                select(ScriptLineRevisionAssociation).where(
                    ScriptLineRevisionAssociation.revision_id == revision2_id
                )
            ).all()
            self.assertEqual(3, len(rev2_assocs))

        # Now branch from revision 1 (which has 2 lines)
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "description": "Branch from revision 1",
                    "parent_revision_id": self.revision1_id,
                    "set_as_current": False,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        branch_revision_id = tornado.escape.json_decode(response.body)["id"]

        # Verify the branch has 2 line associations (from revision 1, not 3 from revision 2)
        with self._app.get_db().sessionmaker() as session:
            branch_assocs = session.scalars(
                select(ScriptLineRevisionAssociation).where(
                    ScriptLineRevisionAssociation.revision_id == branch_revision_id
                )
            ).all()
            self.assertEqual(
                2,
                len(branch_assocs),
                "Branch should copy 2 lines from revision 1 parent, not 3 from current revision 2",
            )

            # Verify current revision is still revision 2
            script = session.get(Script, self.script_id)
            self.assertEqual(revision2_id, script.current_revision)


class TestScriptRevisionDeletionTreeIntegrity(DigiScriptTestCase):
    """Test that deleting middle nodes maintains tree integrity.

    When deleting a revision in the middle of a chain (A→B→C), the children
    of the deleted revision should be updated to point to the deleted revision's
    parent, maintaining a connected tree.
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

            # Create revision 1 (A)
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Revision A"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id
            script.current_revision = revision1.id

            # Create revision 2 (B) - child of A
            revision2 = ScriptRevision(
                script_id=script.id,
                revision=2,
                description="Revision B",
                previous_revision_id=revision1.id,
            )
            session.add(revision2)
            session.flush()
            self.revision2_id = revision2.id

            # Create revision 3 (C) - child of B
            revision3 = ScriptRevision(
                script_id=script.id,
                revision=3,
                description="Revision C",
                previous_revision_id=revision2.id,
            )
            session.add(revision3)
            session.flush()
            self.revision3_id = revision3.id

            # Create revision 4 (D) - another child of B (to test multiple children)
            revision4 = ScriptRevision(
                script_id=script.id,
                revision=4,
                description="Revision D",
                previous_revision_id=revision2.id,
            )
            session.add(revision4)
            session.flush()
            self.revision4_id = revision4.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def test_delete_middle_revision_updates_children(self):
        """Test deleting B in chain A→B→C updates C to point to A.

        Tree before: A → B → C
                         └─→ D

        Tree after deleting B: A → C
                                  └─→ D
        """
        # Delete revision 2 (B)
        response = self.fetch(
            f"/api/v1/show/script/revisions?rev_id={self.revision2_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code)

        # Verify the tree structure is maintained
        with self._app.get_db().sessionmaker() as session:
            # B should be deleted
            deleted_rev = session.get(ScriptRevision, self.revision2_id)
            self.assertIsNone(deleted_rev, "Revision B should be deleted")

            # C should now point to A (not orphaned)
            revision_c = session.get(ScriptRevision, self.revision3_id)
            self.assertEqual(
                self.revision1_id,
                revision_c.previous_revision_id,
                "Revision C should now point to A as parent",
            )

            # D should also point to A (multiple children case)
            revision_d = session.get(ScriptRevision, self.revision4_id)
            self.assertEqual(
                self.revision1_id,
                revision_d.previous_revision_id,
                "Revision D should now point to A as parent",
            )

            # Verify A still exists
            revision_a = session.get(ScriptRevision, self.revision1_id)
            self.assertIsNotNone(revision_a, "Revision A should still exist")

    def test_delete_middle_revision_in_longer_chain(self):
        """Test deleting middle revision in a longer chain A→B→C→D→E.

        After deleting C, D should point to B.
        """
        # Create revision 5 (E) - child of C
        with self._app.get_db().sessionmaker() as session:
            revision5 = ScriptRevision(
                script_id=self.script_id,
                revision=5,
                description="Revision E",
                previous_revision_id=self.revision3_id,  # Child of C
            )
            session.add(revision5)
            session.commit()
            revision5_id = revision5.id

        # Delete revision 3 (C) from chain A→B→C→E
        response = self.fetch(
            f"/api/v1/show/script/revisions?rev_id={self.revision3_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code)

        # Verify E now points to B (C's parent)
        with self._app.get_db().sessionmaker() as session:
            revision_e = session.get(ScriptRevision, revision5_id)
            self.assertEqual(
                self.revision2_id,
                revision_e.previous_revision_id,
                "Revision E should now point to B after C is deleted",
            )
