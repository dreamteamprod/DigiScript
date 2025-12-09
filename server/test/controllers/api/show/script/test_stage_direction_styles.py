import tornado.escape
from sqlalchemy import select

from models.script import Script, ScriptRevision, StageDirectionStyle
from models.show import Show
from test.conftest import DigiScriptTestCase


class TestStageDirectionStylesController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/stage_direction_styles endpoints."""

    def setUp(self):
        super().setUp()
        # Create base test data
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
            self.script_id = script.id

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()

            script.current_revision = revision.id

            # Create a stage direction style
            style = StageDirectionStyle(
                script_id=script.id,
                description="Test Style",
                bold=True,
                italic=False,
                underline=False,
                text_format="default",
                text_colour="#000000",
                enable_background_colour=False,
                background_colour=None,
            )
            session.add(style)
            session.commit()
            self.style_id = style.id

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_stage_direction_styles(self):
        """Test GET /api/v1/show/script/stage_direction_styles.

        This tests the query at line 24:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/script/stage_direction_styles")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("styles", response_body)
        self.assertEqual(1, len(response_body["styles"]))
        self.assertEqual("Test Style", response_body["styles"][0]["description"])

    def test_get_stage_direction_styles_empty(self):
        """Test GET returns empty list when no styles exist."""
        # Create a show with a script but no styles
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Show 2")
            session.add(show2)
            session.flush()

            script2 = Script(show_id=show2.id)
            session.add(script2)
            session.flush()

            revision2 = ScriptRevision(
                script_id=script2.id, revision=1, description="Initial"
            )
            session.add(revision2)
            session.flush()

            script2.current_revision = revision2.id
            session.commit()
            show2_id = show2.id

        self._app.digi_settings.settings["current_show"].set_value(show2_id)

        response = self.fetch("/api/v1/show/script/stage_direction_styles")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual([], response_body["styles"])
