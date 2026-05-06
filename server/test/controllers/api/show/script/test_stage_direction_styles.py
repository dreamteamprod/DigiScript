import tornado.escape

from models.script import Script, ScriptRevision, StageDirectionStyle
from models.show import Show, ShowScriptType
from test.conftest import DigiScriptTestCase


class TestStageDirectionStylesController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/stage_direction_styles endpoints."""

    def setUp(self):
        super().setUp()
        # Create base test data
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
            show2 = Show(name="Show 2", script_mode=ShowScriptType.FULL)
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


class TestStageDirectionStylesImport(DigiScriptTestCase):
    """Test suite for GET /api/v1/show/script/stage_direction_styles/import."""

    IMPORT_URL = "/api/v1/show/script/stage_direction_styles/import"

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            current_show = Show(name="Current Show", script_mode=ShowScriptType.FULL)
            session.add(current_show)
            session.flush()
            self.current_show_id = current_show.id

            current_script = Script(show_id=current_show.id)
            session.add(current_script)
            session.flush()
            current_revision = ScriptRevision(
                script_id=current_script.id, revision=1, description="Initial"
            )
            session.add(current_revision)
            session.flush()
            current_script.current_revision = current_revision.id

            current_style = StageDirectionStyle(
                script_id=current_script.id,
                description="Current Show Style",
                bold=False,
                italic=False,
                underline=False,
                text_format="default",
                text_colour="#111111",
                enable_background_colour=False,
                background_colour=None,
            )
            session.add(current_style)

            other_show = Show(name="Other Show", script_mode=ShowScriptType.FULL)
            session.add(other_show)
            session.flush()
            self.other_show_id = other_show.id

            other_script = Script(show_id=other_show.id)
            session.add(other_script)
            session.flush()
            other_revision = ScriptRevision(
                script_id=other_script.id, revision=1, description="Initial"
            )
            session.add(other_revision)
            session.flush()
            other_script.current_revision = other_revision.id

            other_style = StageDirectionStyle(
                script_id=other_script.id,
                description="Other Show Style",
                bold=True,
                italic=False,
                underline=False,
                text_format="upper",
                text_colour="#222222",
                enable_background_colour=False,
                background_colour=None,
            )
            session.add(other_style)

            empty_show = Show(name="Empty Show", script_mode=ShowScriptType.FULL)
            session.add(empty_show)
            session.flush()
            self.empty_show_id = empty_show.id

            empty_script = Script(show_id=empty_show.id)
            session.add(empty_script)
            session.flush()
            empty_revision = ScriptRevision(
                script_id=empty_script.id, revision=1, description="Initial"
            )
            session.add(empty_revision)
            session.flush()
            empty_script.current_revision = empty_revision.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.current_show_id)

    def _login_admin(self):
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=tornado.escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )
        resp = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=tornado.escape.json_encode(
                {"username": "admin", "password": "adminpass"}
            ),
        )
        return tornado.escape.json_decode(resp.body)["access_token"]

    def test_get_import_requires_auth(self):
        """GET without auth token returns 401."""
        response = self.fetch(self.IMPORT_URL)
        self.assertEqual(401, response.code)

    def test_get_import_requires_show(self):
        """GET with auth but no current show returns 400."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        token = self._login_admin()
        response = self.fetch(
            self.IMPORT_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(400, response.code)

    def test_get_import_excludes_current_show(self):
        """Current show's styles must not appear in the import response."""
        token = self._login_admin()
        response = self.fetch(
            self.IMPORT_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        show_ids = [s["id"] for s in body["style_groups"]]
        self.assertNotIn(self.current_show_id, show_ids)

    def test_get_import_includes_other_shows(self):
        """Other shows with styles are returned with correct name and style data."""
        token = self._login_admin()
        response = self.fetch(
            self.IMPORT_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        other = next(
            (s for s in body["style_groups"] if s["id"] == self.other_show_id), None
        )
        self.assertIsNotNone(other)
        self.assertEqual("Other Show", other["name"])
        self.assertEqual(1, len(other["styles"]))
        self.assertEqual("Other Show Style", other["styles"][0]["description"])
        self.assertEqual("upper", other["styles"][0]["text_format"])

    def test_get_import_skips_shows_with_no_styles(self):
        """Shows that have a script but no styles are omitted from the response."""
        token = self._login_admin()
        response = self.fetch(
            self.IMPORT_URL,
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        show_ids = [s["id"] for s in body["style_groups"]]
        self.assertNotIn(self.empty_show_id, show_ids)
