import tornado.escape
from sqlalchemy import select

from models.cue import CueType
from models.script import (
    Script,
    ScriptLine,
    ScriptLineRevisionAssociation,
    ScriptLineType,
    ScriptRevision,
)
from models.show import Act, Scene, Show, ShowScriptType
from models.user import User
from test.conftest import DigiScriptTestCase


class TestCueController(DigiScriptTestCase):
    """Test suite for /api/v1/show/cues endpoint."""

    def setUp(self):
        super().setUp()
        # Create a test show with script
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
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_cues(self):
        """Test GET /api/v1/show/cues.

        This tests two queries in cues.py:
        - Line 176-177: Script lookup
          session.scalars(select(Script).where(Script.show_id == show.id)).first()
        - Line 190-193: CueAssociation filter
          session.scalars(select(CueAssociation).where(...)).all()
        """
        response = self.fetch("/api/v1/show/cues")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("cues", response_body)

    def test_get_cues_no_script(self):
        """Test GET returns error when no script exists."""
        # Create a show without a script
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Show 2", script_mode=ShowScriptType.FULL)
            session.add(show2)
            session.flush()
            show2_id = show2.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show2_id)

        response = self.fetch("/api/v1/show/cues")
        # Should get an error because there's no script
        self.assertNotEqual(200, response.code)


class TestCueStatsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/cues/stats endpoint."""

    def setUp(self):
        super().setUp()
        # Create a test show with script
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
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_cue_stats(self):
        """Test GET /api/v1/show/cues/stats.

        This tests the query at line 455-456 in cues.py:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/cues/stats")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("cue_counts", response_body)


class TestSpacingLineCueRestriction(DigiScriptTestCase):
    """Test suite for spacing line cue restriction."""

    def setUp(self):
        super().setUp()
        # Create comprehensive test data
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
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id
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

            # Create a SPACING line
            spacing_line = ScriptLine(
                act_id=act.id,
                scene_id=scene.id,
                page=1,
                line_type=ScriptLineType.SPACING,
            )
            session.add(spacing_line)
            session.flush()
            self.spacing_line_id = spacing_line.id

            # Add line to revision
            assoc = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=spacing_line.id
            )
            session.add(assoc)

            # Create a regular DIALOGUE line for comparison
            dialogue_line = ScriptLine(
                act_id=act.id,
                scene_id=scene.id,
                page=1,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(dialogue_line)
            session.flush()
            self.dialogue_line_id = dialogue_line.id

            # Add dialogue line to revision
            assoc2 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=dialogue_line.id
            )
            session.add(assoc2)

            # Create cue type
            cue_type = CueType(
                show_id=show.id,
                prefix="LX",
                description="Lighting",
                colour="#ff0000",
            )
            session.add(cue_type)
            session.flush()
            self.cue_type_id = cue_type.id

            # Create admin user for RBAC
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            self.user_id = admin.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def test_post_cue_rejects_spacing_line(self):
        """
        Test adding a cue to a SPACING line returns 400.
        """
        cue_data = {
            "cueType": self.cue_type_id,
            "ident": "LX 1",
            "lineId": self.spacing_line_id,
        }

        response = self.fetch(
            "/api/v1/show/cues",
            method="POST",
            body=tornado.escape.json_encode(cue_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(
            "Cannot add cues to spacing lines",
            response_body["message"],
            "Should reject cue on SPACING line with specific error message",
        )

        # Verify no cue was created
        with self._app.get_db().sessionmaker() as session:
            from models.cue import CueAssociation

            cue_assocs = session.scalars(select(CueAssociation)).all()
            self.assertEqual(
                0,
                len(cue_assocs),
                "No CueAssociation should be created for SPACING line",
            )

    def test_post_cue_allows_dialogue_line(self):
        """
        Test adding a cue to a DIALOGUE line succeeds (regression test).

        Verifies that the SPACING restriction doesn't affect other line types.
        """
        cue_data = {
            "cueType": self.cue_type_id,
            "ident": "LX 1",
            "lineId": self.dialogue_line_id,
        }

        response = self.fetch(
            "/api/v1/show/cues",
            method="POST",
            body=tornado.escape.json_encode(cue_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code, "DIALOGUE line should accept cues")

        # Verify cue was created
        with self._app.get_db().sessionmaker() as session:
            from models.cue import CueAssociation

            cue_assocs = session.scalars(select(CueAssociation)).all()
            self.assertEqual(
                1,
                len(cue_assocs),
                "CueAssociation should be created for DIALOGUE line",
            )
            self.assertEqual(self.dialogue_line_id, cue_assocs[0].line_id)
