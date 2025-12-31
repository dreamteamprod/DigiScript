"""Tests for orphaned object deletion (Issue #768).

This module tests that orphaned script lines, line parts, cuts, and cues
are properly deleted when all references are removed.
"""

from test.conftest import DigiScriptTestCase

import tornado.escape
from sqlalchemy import select

from models.cue import Cue, CueAssociation, CueType
from models.script import (
    Script,
    ScriptCuts,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptRevision,
)
from models.show import Act, Character, Scene, Show, ShowScriptType


class TestOrphanedLineDeletion(DigiScriptTestCase):
    """Test deleting lines via PATCH verifies orphaned objects are cleaned up.

    Tests the fix for Issue #768 where orphaned script_lines persist in the
    database after deletion from a revision.
    """

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            from models.user import User

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

            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision_id = revision1.id
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

    def test_delete_line_via_patch_deletes_orphaned_line(self):
        """Test deleting a line via PATCH removes orphaned ScriptLine.

        This is the core test for Issue #768. When a line is deleted from a
        revision and has no other references, it should be deleted from the
        database.
        """
        # Create initial lines via API
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
            },
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
                        "line_text": "Line 2 - to be deleted",
                    }
                ],
                "stage_direction_style_id": None,
            },
        ]

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(initial_lines),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Get created line IDs
        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="GET",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        page_data = tornado.escape.json_decode(response.body)
        line1_id = page_data["lines"][0]["id"]
        line2_id = page_data["lines"][1]["id"]
        line2_part_id = page_data["lines"][1]["line_parts"][0]["id"]

        # Verify we have 2 lines before deletion
        with self._app.get_db().sessionmaker() as session:
            all_lines = session.scalars(select(ScriptLine)).all()
            self.assertEqual(2, len(all_lines), "Should have 2 lines before deletion")

        # Delete line 2 via PATCH - need to include both lines, mark line 2 as deleted
        all_lines = [
            {
                "id": line1_id,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "stage_direction": False,
                "line_parts": [
                    {
                        "id": page_data["lines"][0]["line_parts"][0]["id"],
                        "line_id": line1_id,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": "Line 1",
                    }
                ],
                "stage_direction_style_id": None,
            },
            {
                "id": line2_id,  # Line to be deleted - include ID for lookup
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "stage_direction": False,
                "line_parts": page_data["lines"][1]["line_parts"],
                "stage_direction_style_id": None,
            },
        ]

        patch_data = {
            "page": all_lines,
            "status": {"added": [], "updated": [], "deleted": [1], "inserted": []},
        }

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="PATCH",
            body=tornado.escape.json_encode(patch_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code, "PATCH should succeed")

        # Verify orphaned line is deleted
        with self._app.get_db().sessionmaker() as session:
            # 1. Orphaned line should be deleted
            line2 = session.get(ScriptLine, line2_id)
            self.assertIsNone(line2, "Orphaned line should be deleted")

            # 2. Orphaned line_part should be cascade deleted
            line2_part = session.get(ScriptLinePart, line2_part_id)
            self.assertIsNone(line2_part, "Orphaned line_part should be deleted")

            # 3. Only 1 line should remain
            all_lines = session.scalars(select(ScriptLine)).all()
            self.assertEqual(1, len(all_lines), "Should have exactly 1 line")

            # 4. Line 1 should still exist
            line1 = session.get(ScriptLine, line1_id)
            self.assertIsNotNone(line1, "Line 1 should still exist")

    def test_delete_line_with_cuts_cascades_properly(self):
        """Test deleting a line with ScriptCuts verifies full cascade.

        Verifies that when a line is deleted:
        1. ScriptLine is deleted
        2. ScriptLinePart cascades via cascade="all, delete-orphan"
        3. ScriptCuts cascades via cascade="all, delete-orphan" on ScriptLinePart
        """
        # Create initial line via API
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
                        "line_text": "Line with cut",
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

        # Get created line ID
        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="GET",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        page_data = tornado.escape.json_decode(response.body)
        line_id = page_data["lines"][0]["id"]
        line_part_id = page_data["lines"][0]["line_parts"][0]["id"]

        # Add a cut to the line_part
        with self._app.get_db().sessionmaker() as session:
            cut = ScriptCuts(revision_id=self.revision_id, line_part_id=line_part_id)
            session.add(cut)
            session.commit()

        # Verify cut exists
        with self._app.get_db().sessionmaker() as session:
            cuts = session.scalars(select(ScriptCuts)).all()
            self.assertEqual(1, len(cuts), "Should have 1 cut before deletion")

        # Delete the line via PATCH - include line with ID
        lines_to_send = [
            {
                "id": line_id,  # Line to be deleted - include ID for lookup
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "stage_direction": False,
                "line_parts": page_data["lines"][0]["line_parts"],
                "stage_direction_style_id": None,
            }
        ]

        patch_data = {
            "page": lines_to_send,
            "status": {"added": [], "updated": [], "deleted": [0], "inserted": []},
        }

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="PATCH",
            body=tornado.escape.json_encode(patch_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code, "PATCH should succeed")

        # Verify full cascade deletion
        with self._app.get_db().sessionmaker() as session:
            # 1. Line should be deleted
            line = session.get(ScriptLine, line_id)
            self.assertIsNone(line, "Line should be deleted")

            # 2. Line_part should be cascade deleted
            line_part = session.get(ScriptLinePart, line_part_id)
            self.assertIsNone(line_part, "Line_part should be cascade deleted")

            # 3. ScriptCuts should be cascade deleted
            cuts = session.scalars(select(ScriptCuts)).all()
            self.assertEqual(
                0, len(cuts), "ScriptCuts should be cascade deleted from line_part"
            )

            # 4. No lines should remain
            all_lines = session.scalars(select(ScriptLine)).all()
            self.assertEqual(0, len(all_lines), "No lines should remain")

    def test_delete_cue_association_deletes_orphaned_cue(self):
        """Test deleting a CueAssociation removes orphaned Cue.

        This tests the fix in CueAssociation.post_delete() which had the same
        bug as ScriptLineRevisionAssociation.
        """
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
            self.cue_type_id = cue_type.id
            session.commit()

        # Create a line with a cue via API
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
                        "line_text": "Line with cue",
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

        # Get created line ID
        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="GET",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        page_data = tornado.escape.json_decode(response.body)
        line_id = page_data["lines"][0]["id"]

        # Add a cue to the line
        with self._app.get_db().sessionmaker() as session:
            cue = Cue(cue_type_id=self.cue_type_id, ident="LX1")
            session.add(cue)
            session.flush()
            cue_id = cue.id

            cue_assoc = CueAssociation(
                revision_id=self.revision_id, line_id=line_id, cue_id=cue_id
            )
            session.add(cue_assoc)
            session.commit()

        # Verify cue exists
        with self._app.get_db().sessionmaker() as session:
            cues = session.scalars(select(Cue)).all()
            self.assertEqual(1, len(cues), "Should have 1 cue before deletion")

        # Delete the line (which will delete the cue association) - include line with ID
        lines_to_send = [
            {
                "id": line_id,  # Line to be deleted - include ID for lookup
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "stage_direction": False,
                "line_parts": page_data["lines"][0]["line_parts"],
                "stage_direction_style_id": None,
            }
        ]

        patch_data = {
            "page": lines_to_send,
            "status": {"added": [], "updated": [], "deleted": [0], "inserted": []},
        }

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="PATCH",
            body=tornado.escape.json_encode(patch_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code, "PATCH should succeed")

        # Verify orphaned cue is deleted
        with self._app.get_db().sessionmaker() as session:
            # 1. Cue should be deleted (orphaned)
            cue = session.get(Cue, cue_id)
            self.assertIsNone(cue, "Orphaned cue should be deleted")

            # 2. CueAssociation should be deleted
            cue_assocs = session.scalars(select(CueAssociation)).all()
            self.assertEqual(0, len(cue_assocs), "Cue associations should be deleted")

            # 3. Line should be deleted
            line = session.get(ScriptLine, line_id)
            self.assertIsNone(line, "Line should be deleted")
