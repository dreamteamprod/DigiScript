from test.conftest import DigiScriptTestCase

import tornado.escape
from sqlalchemy import select

from models.cue import Cue, CueAssociation, CueType
from models.script import (
    ScriptLineType,
    Script,
    ScriptCuts,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptRevision,
)
from models.show import Act, Character, Scene, Show, ShowScriptType
from models.user import User
from rbac.role import Role


class TestScriptController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script endpoints."""

    def setUp(self):
        super().setUp()
        # Create base test data that many tests will need
        with self._app.get_db().sessionmaker() as session:
            # Create a test show
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create script and revision
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Rev"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id

            # Link revision to script
            script.current_revision = revision.id

            # Create act and scene for lines
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()
            self.act_id = act.id

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            self.scene_id = scene.id

            # Create a character for line parts
            character = Character(show_id=show.id, name="Test Character")
            session.add(character)
            session.flush()
            self.character_id = character.id

            # Create admin user for RBAC
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()

            session.commit()

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_script_page_no_page_param(self):
        """Test GET /api/v1/show/script without page parameter returns 400."""
        response = self.fetch("/api/v1/show/script")
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("Page not given", response_body["message"])

    def test_get_script_page_with_no_lines(self):
        """Test GET /api/v1/show/script?page=1 with empty script.

        This tests the query at line 59-66:
        session.scalars(
            select(ScriptLineRevisionAssociation).where(
                ScriptLineRevisionAssociation.revision_id == revision.id,
                ScriptLineRevisionAssociation.line.has(page=page),
            )
        ).all()
        """
        response = self.fetch("/api/v1/show/script?page=1")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual([], response_body["lines"])
        self.assertEqual(1, response_body["page"])

    def test_get_script_page_with_lines(self):
        """Test GET /api/v1/show/script?page=1 with actual script lines.

        This tests multiple queries including:
        - Line 47: session.query(Script).filter(Script.show_id == show.id).first()
        - Line 59-66: ScriptLineRevisionAssociation with .has() filter
        - Line 91-97: session.get() with composite key dict
        """
        # Create script lines
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)

            # Create first line
            line1 = ScriptLine(
                act_id=self.act_id,
                scene_id=self.scene_id,
                page=1,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(line1)
            session.flush()

            part1 = ScriptLinePart(
                line_id=line1.id,
                part_index=0,
                character_id=self.character_id,
                line_text="Hello world",
            )
            session.add(part1)

            assoc1 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line1.id
            )
            session.add(assoc1)
            session.flush()

            # Create second line
            line2 = ScriptLine(
                act_id=self.act_id,
                scene_id=self.scene_id,
                page=1,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(line2)
            session.flush()

            part2 = ScriptLinePart(
                line_id=line2.id,
                part_index=0,
                character_id=self.character_id,
                line_text="Goodbye world",
            )
            session.add(part2)

            assoc2 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line2.id, previous_line_id=line1.id
            )
            session.add(assoc2)

            # Update first association
            assoc1.next_line_id = line2.id

            session.commit()

        response = self.fetch("/api/v1/show/script?page=1")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["lines"]))
        self.assertEqual(1, response_body["page"])

    def test_composite_key_get_pattern_used_throughout(self):
        """Verify the composite key .get() pattern is used in POST/PATCH.

        POST and PATCH methods use composite dict .get() extensively (lines 91-97,
        259-266, 416-419, 440-447, 511-518, 529-531, etc). These follow the same
        pattern already tested in test_script_models.py for the compile_script method.

        This test verifies the pattern works by directly using it.
        """
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)

            # Create a line and association
            line = ScriptLine(
                act_id=self.act_id,
                scene_id=self.scene_id,
                page=1,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(line)
            session.flush()

            assoc = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line.id
            )
            session.add(assoc)
            session.commit()
            line_id = line.id

        # Test the composite key .get() pattern (SQLAlchemy 2.0 uses tuple)
        with self._app.get_db().sessionmaker() as session:
            # SQLAlchemy 2.0 pattern for composite primary keys
            found_assoc = session.get(
                ScriptLineRevisionAssociation, (self.revision_id, line_id)
            )
            self.assertIsNotNone(found_assoc)
            self.assertEqual(self.revision_id, found_assoc.revision_id)
            self.assertEqual(line_id, found_assoc.line_id)


class TestCompiledScriptController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/compiled endpoint."""

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

            revision = ScriptRevision(script_id=script.id, revision=1)
            session.add(revision)
            session.flush()

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_compiled_script(self):
        """Test GET /api/v1/show/script/compiled.

        This tests the query at line 666:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/script/compiled")
        # Empty script won't have compiled form yet, so expect 404
        self.assertEqual(404, response.code)


class TestScriptCutsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/cuts endpoint."""

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

            revision = ScriptRevision(script_id=script.id, revision=1)
            session.add(revision)
            session.flush()
            self.revision_id = revision.id

            script.current_revision = revision.id

            # Create a line part for cuts
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()

            character = Character(show_id=show.id, name="Test Character")
            session.add(character)
            session.flush()

            line = ScriptLine(
                act_id=act.id,
                scene_id=scene.id,
                page=1,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(line)
            session.flush()

            line_part = ScriptLinePart(
                line_id=line.id,
                part_index=0,
                character_id=character.id,
                line_text="Test",
            )
            session.add(line_part)
            session.flush()
            self.line_part_id = line_part.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_script_cuts(self):
        """Test GET /api/v1/show/script/cuts.

        This tests the queries at lines 705 and 717-721:
        - session.query(Script).filter(Script.show_id == show.id).first()
        - session.query(ScriptCuts).filter(ScriptCuts.revision_id == revision.id).all()
        """
        response = self.fetch("/api/v1/show/script/cuts")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual([], response_body["cuts"])

    def test_script_cuts_query_patterns(self):
        """Test the query patterns used in PUT /api/v1/show/script/cuts.

        This tests the queries at lines 741 and 766-770 by using them directly:
        - session.query(Script).filter(Script.show_id == show.id).first()
        - session.query(ScriptCuts).filter(ScriptCuts.revision_id == revision.id).all()
        """
        # Create a cut directly to test the query pattern
        with self._app.get_db().sessionmaker() as session:
            cut = ScriptCuts(
                line_part_id=self.line_part_id, revision_id=self.revision_id
            )
            session.add(cut)
            session.commit()

        # Test the query patterns used in the controller
        with self._app.get_db().sessionmaker() as session:
            # Pattern 1: Get script by show_id (line 741)
            script = session.scalars(
                select(Script).where(Script.show_id == self.show_id)
            ).first()
            self.assertIsNotNone(script)

            # Pattern 2: Get all cuts for revision (lines 766-770)
            cuts = session.scalars(
                select(ScriptCuts).where(ScriptCuts.revision_id == self.revision_id)
            ).all()
            self.assertEqual(1, len(cuts))
            self.assertEqual(self.line_part_id, cuts[0].line_part_id)


class TestScriptMaxPageController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/max_page endpoint."""

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

            revision = ScriptRevision(script_id=script.id, revision=1)
            session.add(revision)
            session.flush()
            self.revision_id = revision.id

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_max_page_empty_script(self):
        """Test GET /api/v1/show/script/max_page with no lines.

        This tests the queries at lines 804 and 816-826:
        - session.query(Script).filter(Script.show_id == show.id).first()
        - session.query(...).with_entities(ScriptLineRevisionAssociation.line_id).filter(...)
        - session.query(...).with_entities(func.max(ScriptLine.page)).where(...).first()[0]
        """
        response = self.fetch("/api/v1/show/script/max_page")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(0, response_body["max_page"])

    def test_get_max_page_with_lines(self):
        """Test GET /api/v1/show/script/max_page with lines on multiple pages."""
        # Create lines on pages 1 and 2
        with self._app.get_db().sessionmaker() as session:
            revision = session.get(ScriptRevision, self.revision_id)

            act = Act(show_id=self.show_id, name="Act 1")
            session.add(act)
            session.flush()

            scene = Scene(show_id=self.show_id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()

            # Page 1 line
            line1 = ScriptLine(
                act_id=act.id,
                scene_id=scene.id,
                page=1,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(line1)
            session.flush()

            assoc1 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line1.id
            )
            session.add(assoc1)

            # Page 2 line
            line2 = ScriptLine(
                act_id=act.id,
                scene_id=scene.id,
                page=2,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(line2)
            session.flush()

            assoc2 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line2.id
            )
            session.add(assoc2)

            session.commit()

        response = self.fetch("/api/v1/show/script/max_page")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, response_body["max_page"])


class TestScriptUpdateWithAssociations(DigiScriptTestCase):
    """Test updating script lines with revision-scoped associations (Issue #670).

    When updating a line via PATCH, DigiScript creates new ScriptLine and
    ScriptLinePart objects. All revision-scoped associations (CueAssociation,
    ScriptCuts) must be migrated to the new objects, not cascade deleted.
    """

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

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id
            script.current_revision = revision.id

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

            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            self.user_id = admin.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def test_update_line_with_cue_attached(self):
        """Test updating a line that has a cue attached.

        Verifies that CueAssociation is migrated to the new line object.
        """
        # Create initial line
        initial_lines = [
            {
                "id": None,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": "Original text",
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

        # Add cue to the line
        with self._app.get_db().sessionmaker() as session:
            cue_type = CueType(
                show_id=self.show_id,
                prefix="LX",
                description="Lighting",
                colour="#ff0000",
            )
            session.add(cue_type)
            session.flush()

            cue = Cue(cue_type_id=cue_type.id, ident="LX 1")
            session.add(cue)
            session.flush()

            cue_assoc = CueAssociation(
                revision_id=self.revision_id, line_id=line_id, cue_id=cue.id
            )
            session.add(cue_assoc)
            session.commit()

        # Update the line
        updated_lines = [
            {
                "id": line_id,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": line_part_id,
                        "line_id": line_id,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": "Updated text",
                    }
                ],
                "stage_direction_style_id": None,
            }
        ]

        patch_data = {
            "page": updated_lines,
            "status": {"added": [], "updated": [0], "deleted": [], "inserted": []},
        }

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="PATCH",
            body=tornado.escape.json_encode(patch_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code, "PATCH should succeed")

        # Verify cue was migrated and old objects cleaned up
        with self._app.get_db().sessionmaker() as session:
            # 1. Should have exactly 1 cue association (old one deleted, new one created)
            cue_assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.revision_id == self.revision_id
                )
            ).all()
            self.assertEqual(1, len(cue_assocs), "Should have 1 cue association")

            # 2. Cue association should point to NEW line (not the old one)
            new_line_id = cue_assocs[0].line_id
            self.assertNotEqual(line_id, new_line_id, "Cue should point to NEW line")

            # 3. Old line should be deleted
            old_line = session.get(ScriptLine, line_id)
            self.assertIsNone(old_line, "Old line should be deleted")

            # 4. Old line_part should be deleted
            old_line_part = session.get(ScriptLinePart, line_part_id)
            self.assertIsNone(old_line_part, "Old line_part should be deleted")

            # 5. New line should exist
            new_line = session.get(ScriptLine, new_line_id)
            self.assertIsNotNone(new_line, "New line should exist")

            # 6. Exactly 1 line should exist (the new one)
            all_lines = session.scalars(select(ScriptLine)).all()
            self.assertEqual(1, len(all_lines), "Should have exactly 1 line")

    def test_update_line_with_cut_attached(self):
        """Test updating a line that has a line_part cut.

        Verifies that ScriptCuts is migrated to the new line_part object.
        """
        # Create initial line
        initial_lines = [
            {
                "id": None,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": "This line will be cut",
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

        # Mark line_part as cut
        with self._app.get_db().sessionmaker() as session:
            cut = ScriptCuts(revision_id=self.revision_id, line_part_id=line_part_id)
            session.add(cut)
            session.commit()

        # Update the line
        updated_lines = [
            {
                "id": line_id,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": line_part_id,
                        "line_id": line_id,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": "Updated cut line",
                    }
                ],
                "stage_direction_style_id": None,
            }
        ]

        patch_data = {
            "page": updated_lines,
            "status": {"added": [], "updated": [0], "deleted": [], "inserted": []},
        }

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="PATCH",
            body=tornado.escape.json_encode(patch_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code, "PATCH should succeed")

        # Verify cut was migrated and old objects cleaned up
        with self._app.get_db().sessionmaker() as session:
            # 1. Should have exactly 1 cut (old one deleted, new one created)
            cuts = session.scalars(
                select(ScriptCuts).where(ScriptCuts.revision_id == self.revision_id)
            ).all()
            self.assertEqual(1, len(cuts), "Should have 1 cut")

            # 2. Cut should point to NEW line_part (not the old one)
            new_line_part_id = cuts[0].line_part_id
            self.assertNotEqual(
                line_part_id, new_line_part_id, "Cut should point to NEW line_part"
            )

            # 3. Old line_part should be deleted
            old_line_part = session.get(ScriptLinePart, line_part_id)
            self.assertIsNone(old_line_part, "Old line_part should be deleted")

            # 4. Old line should be deleted
            old_line = session.get(ScriptLine, line_id)
            self.assertIsNone(old_line, "Old line should be deleted")

            # 5. New line_part should exist
            new_line_part = session.get(ScriptLinePart, new_line_part_id)
            self.assertIsNotNone(new_line_part, "New line_part should exist")

            # 6. Exactly 1 line should exist (the new one)
            all_lines = session.scalars(select(ScriptLine)).all()
            self.assertEqual(1, len(all_lines), "Should have exactly 1 line")

    def test_update_line_with_both_cue_and_cut(self):
        """Test updating a line that has both a cue and a cut.

        Comprehensive test ensuring both CueAssociation and ScriptCuts are migrated.
        """
        # Create initial line
        initial_lines = [
            {
                "id": None,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": "Line with cue and cut",
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

        # Add both cue and cut
        with self._app.get_db().sessionmaker() as session:
            cue_type = CueType(
                show_id=self.show_id,
                prefix="LX",
                description="Lighting",
                colour="#ff0000",
            )
            session.add(cue_type)
            session.flush()

            cue = Cue(cue_type_id=cue_type.id, ident="LX 1")
            session.add(cue)
            session.flush()

            cue_assoc = CueAssociation(
                revision_id=self.revision_id, line_id=line_id, cue_id=cue.id
            )
            session.add(cue_assoc)

            cut = ScriptCuts(revision_id=self.revision_id, line_part_id=line_part_id)
            session.add(cut)

            session.commit()

        # Update the line
        updated_lines = [
            {
                "id": line_id,
                "act_id": self.act_id,
                "scene_id": self.scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": line_part_id,
                        "line_id": line_id,
                        "part_index": 0,
                        "character_id": self.character_id,
                        "character_group_id": None,
                        "line_text": "Updated line with cue and cut",
                    }
                ],
                "stage_direction_style_id": None,
            }
        ]

        patch_data = {
            "page": updated_lines,
            "status": {"added": [], "updated": [0], "deleted": [], "inserted": []},
        }

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="PATCH",
            body=tornado.escape.json_encode(patch_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code, "PATCH should succeed")

        # Verify both cue and cut were migrated and old objects cleaned up
        with self._app.get_db().sessionmaker() as session:
            # 1. CueAssociation should be migrated
            cue_assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.revision_id == self.revision_id
                )
            ).all()
            self.assertEqual(1, len(cue_assocs), "Should have 1 cue association")
            new_line_id = cue_assocs[0].line_id
            self.assertNotEqual(line_id, new_line_id, "Cue should point to NEW line")

            # 2. ScriptCuts should be migrated
            cuts = session.scalars(
                select(ScriptCuts).where(ScriptCuts.revision_id == self.revision_id)
            ).all()
            self.assertEqual(1, len(cuts), "Should have 1 cut")
            new_line_part_id = cuts[0].line_part_id
            self.assertNotEqual(
                line_part_id, new_line_part_id, "Cut should point to NEW line_part"
            )

            # 3. Old line should be deleted
            old_line = session.get(ScriptLine, line_id)
            self.assertIsNone(old_line, "Old line should be deleted")

            # 4. Old line_part should be deleted
            old_line_part = session.get(ScriptLinePart, line_part_id)
            self.assertIsNone(old_line_part, "Old line_part should be deleted")

            # 5. New line should exist
            new_line = session.get(ScriptLine, new_line_id)
            self.assertIsNotNone(new_line, "New line should exist")

            # 6. New line_part should exist
            new_line_part = session.get(ScriptLinePart, new_line_part_id)
            self.assertIsNotNone(new_line_part, "New line_part should exist")

            # 7. Exactly 1 line should exist (the new one)
            all_lines = session.scalars(select(ScriptLine)).all()
            self.assertEqual(1, len(all_lines), "Should have exactly 1 line")

    def test_post_compact_mode_rejects_multiple_line_parts(self):
        """Test that POST rejects multiple line_parts in COMPACT mode."""
        # Create show with COMPACT mode
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Compact Show", script_mode=ShowScriptType.COMPACT)
            session.add(show)
            session.flush()
            show_id = show.id

            # Create script and revision
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Rev"
            )
            session.add(revision)
            session.flush()
            revision_id = revision.id
            script.current_revision = revision_id

            # Create act and scene
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()
            act_id = act.id

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            scene_id = scene.id

            # Create TWO characters for multi-part line
            char1 = Character(show_id=show.id, name="Character 1")
            char2 = Character(show_id=show.id, name="Character 2")
            session.add_all([char1, char2])
            session.flush()
            char1_id = char1.id
            char2_id = char2.id

            # Create admin user
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            user_id = admin.id
            session.commit()

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(show_id)

        # Create JWT token
        token = self._app.jwt_service.create_access_token(data={"user_id": user_id})

        # Prepare line with MULTIPLE line_parts (should fail)
        lines = [
            {
                "id": None,
                "act_id": act_id,
                "scene_id": scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": char1_id,
                        "character_group_id": None,
                        "line_text": "First character speaks",
                    },
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 1,
                        "character_id": char2_id,
                        "character_group_id": None,
                        "line_text": "Second character speaks",
                    },
                ],
                "stage_direction_style_id": None,
            }
        ]

        # Make POST request
        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(lines),
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify error response
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn(
            "Lines can only have 1 line part in compact script mode",
            response_body["message"],
        )

    def test_post_compact_mode_accepts_single_line_part(self):
        """Test that POST accepts single line_part in COMPACT mode."""
        # Create show with COMPACT mode
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Compact Show", script_mode=ShowScriptType.COMPACT)
            session.add(show)
            session.flush()
            show_id = show.id

            # Create script and revision
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Rev"
            )
            session.add(revision)
            session.flush()
            revision_id = revision.id
            script.current_revision = revision_id

            # Create act and scene
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()
            act_id = act.id

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            scene_id = scene.id

            # Create one character
            char = Character(show_id=show.id, name="Character 1")
            session.add(char)
            session.flush()
            char_id = char.id

            # Create admin user
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            user_id = admin.id
            session.commit()

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(show_id)

        # Create JWT token
        token = self._app.jwt_service.create_access_token(data={"user_id": user_id})

        # Prepare line with SINGLE line_part (should succeed)
        lines = [
            {
                "id": None,
                "act_id": act_id,
                "scene_id": scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": char_id,
                        "character_group_id": None,
                        "line_text": "Character speaks",
                    }
                ],
                "stage_direction_style_id": None,
            }
        ]

        # Make POST request
        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(lines),
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify success response
        self.assertEqual(200, response.code)

        # Verify in database that line exists with exactly 1 line_part
        with self._app.get_db().sessionmaker() as session:
            script_lines = session.scalars(select(ScriptLine)).all()
            self.assertEqual(1, len(script_lines), "Should have exactly 1 line")

            line_parts = session.scalars(select(ScriptLinePart)).all()
            self.assertEqual(1, len(line_parts), "Should have exactly 1 line_part")

    def test_patch_compact_mode_rejects_multiple_line_parts(self):
        """Test that PATCH rejects updating line to have multiple line_parts in COMPACT mode."""
        # Create show with COMPACT mode and initial line
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Compact Show", script_mode=ShowScriptType.COMPACT)
            session.add(show)
            session.flush()
            show_id = show.id

            # Create script and revision
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Rev"
            )
            session.add(revision)
            session.flush()
            revision_id = revision.id
            script.current_revision = revision_id

            # Create act and scene
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()
            act_id = act.id

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            scene_id = scene.id

            # Create TWO characters
            char1 = Character(show_id=show.id, name="Character 1")
            char2 = Character(show_id=show.id, name="Character 2")
            session.add_all([char1, char2])
            session.flush()
            char1_id = char1.id
            char2_id = char2.id

            # Create admin user
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            user_id = admin.id
            session.commit()

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(show_id)

        # Create JWT token
        token = self._app.jwt_service.create_access_token(data={"user_id": user_id})

        # First, create a line with single line_part (should succeed)
        initial_lines = [
            {
                "id": None,
                "act_id": act_id,
                "scene_id": scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": char1_id,
                        "character_group_id": None,
                        "line_text": "Original line",
                    }
                ],
                "stage_direction_style_id": None,
            }
        ]

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(initial_lines),
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, response.code)

        # Get the line ID
        with self._app.get_db().sessionmaker() as session:
            line = session.scalar(select(ScriptLine))
            line_id = line.id

        # Now try to PATCH the line to have multiple line_parts (should fail)
        updated_lines = [
            {
                "id": line_id,
                "act_id": act_id,
                "scene_id": scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": line_id,
                        "part_index": 0,
                        "character_id": char1_id,
                        "character_group_id": None,
                        "line_text": "First part",
                    },
                    {
                        "id": None,
                        "line_id": line_id,
                        "part_index": 1,
                        "character_id": char2_id,
                        "character_group_id": None,
                        "line_text": "Second part",
                    },
                ],
                "stage_direction_style_id": None,
            }
        ]

        patch_data = {
            "page": updated_lines,
            "status": {"added": [], "updated": [0], "deleted": [], "inserted": []},
        }

        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="PATCH",
            body=tornado.escape.json_encode(patch_data),
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify error response
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn(
            "Lines can only have 1 line part in compact script mode",
            response_body["message"],
        )

        # Verify original line unchanged in database
        with self._app.get_db().sessionmaker() as session:
            line_parts = session.scalars(select(ScriptLinePart)).all()
            self.assertEqual(
                1, len(line_parts), "Should still have exactly 1 line_part"
            )

    def test_full_mode_allows_multiple_line_parts(self):
        """Test that FULL mode allows multiple line_parts (regression test)."""
        # Create show with FULL mode
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Full Mode Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            show_id = show.id

            # Create script and revision
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Test Revision"
            )
            session.add(revision)
            session.flush()
            revision_id = revision.id
            script.current_revision = revision_id

            # Create act and scene
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()
            act_id = act.id

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            scene_id = scene.id

            # Create TWO characters for multi-part line
            char1 = Character(show_id=show.id, name="Character 1")
            char2 = Character(show_id=show.id, name="Character 2")
            session.add_all([char1, char2])
            session.flush()
            char1_id = char1.id
            char2_id = char2.id

            # Create admin user
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            user_id = admin.id
            session.commit()

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(show_id)

        # Create JWT token
        token = self._app.jwt_service.create_access_token(data={"user_id": user_id})

        # Prepare line with MULTIPLE line_parts (should succeed in FULL mode)
        lines = [
            {
                "id": None,
                "act_id": act_id,
                "scene_id": scene_id,
                "page": 1,
                "line_type": 1,
                "line_parts": [
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 0,
                        "character_id": char1_id,
                        "character_group_id": None,
                        "line_text": "First character speaks",
                    },
                    {
                        "id": None,
                        "line_id": None,
                        "part_index": 1,
                        "character_id": char2_id,
                        "character_group_id": None,
                        "line_text": "Second character speaks",
                    },
                ],
                "stage_direction_style_id": None,
            }
        ]

        # Make POST request
        response = self.fetch(
            "/api/v1/show/script?page=1",
            method="POST",
            body=tornado.escape.json_encode(lines),
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify success response
        self.assertEqual(200, response.code)

        # Verify both line_parts were created in database
        with self._app.get_db().sessionmaker() as session:
            line_parts = session.scalars(select(ScriptLinePart)).all()
            self.assertEqual(
                2, len(line_parts), "Should have exactly 2 line_parts in FULL mode"
            )
            # Verify the line_parts have correct text
            line_part_texts = {lp.line_text for lp in line_parts}
            self.assertIn("First character speaks", line_part_texts)
            self.assertIn("Second character speaks", line_part_texts)
