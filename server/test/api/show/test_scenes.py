import tornado.escape

from models.show import Act, Scene, Show
from test.utils import DigiScriptTestCase


class TestSceneController(DigiScriptTestCase):
    """Test suite for /api/v1/show/scene endpoint."""

    def setUp(self):
        super().setUp()
        # Create a test show and act
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            act = Act(show_id=show.id, name="Act 1", interval_after=False)
            session.add(act)
            session.flush()
            self.act_id = act.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_scenes_empty(self):
        """Test GET /api/v1/show/scene with no scenes.

        This tests the query at line 25-26 in scenes.py:
        session.scalars(select(Scene).where(Scene.show_id == show.id)).all()
        """
        response = self.fetch("/api/v1/show/scene")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("scenes", response_body)
        self.assertEqual([], response_body["scenes"])

    def test_get_scenes_with_data(self):
        """Test GET /api/v1/show/scene with existing scenes."""
        # Create test scenes
        with self._app.get_db().sessionmaker() as session:
            scene1 = Scene(
                show_id=self.show_id,
                act_id=self.act_id,
                name="Scene 1",
                previous_scene_id=None,
            )
            scene2 = Scene(
                show_id=self.show_id,
                act_id=self.act_id,
                name="Scene 2",
                previous_scene_id=None,
            )
            session.add(scene1)
            session.add(scene2)
            session.commit()

        response = self.fetch("/api/v1/show/scene")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["scenes"]))
        scene_names = [scene["name"] for scene in response_body["scenes"]]
        self.assertIn("Scene 1", scene_names)
        self.assertIn("Scene 2", scene_names)
