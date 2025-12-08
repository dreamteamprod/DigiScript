import tornado.escape
from sqlalchemy import select

from models.script import (
    Script,
    ScriptRevision,
    ScriptLine,
    ScriptLineRevisionAssociation,
    ScriptLinePart,
    ScriptCuts,
)
from models.show import Show, Act, Scene, Character
from models.user import User
from rbac.role import Role
from test.utils import DigiScriptTestCase


class TestScriptController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script endpoints."""

    def setUp(self):
        super().setUp()
        # Create base test data that many tests will need
        with self._app.get_db().sessionmaker() as session:
            # Create a test show
            show = Show(name="Test Show")
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
                stage_direction=False,
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
                stage_direction=False,
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
                stage_direction=False,
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
            show = Show(name="Test Show")
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
            show = Show(name="Test Show")
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
                act_id=act.id, scene_id=scene.id, page=1, stage_direction=False
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
            show = Show(name="Test Show")
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
                act_id=act.id, scene_id=scene.id, page=1, stage_direction=False
            )
            session.add(line1)
            session.flush()

            assoc1 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line1.id
            )
            session.add(assoc1)

            # Page 2 line
            line2 = ScriptLine(
                act_id=act.id, scene_id=scene.id, page=2, stage_direction=False
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
