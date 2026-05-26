import tornado.escape
from sqlalchemy import select

from models.cue import CueType
from models.mics import Microphone
from models.script import Script, ScriptRevision
from models.session import ShowSession
from models.show import Act, Character, CharacterGroup, Scene, Show, ShowScriptType
from models.user import User
from test.conftest import DigiScriptTestCase


class TestShowsController(DigiScriptTestCase):
    """Test suite for /api/v1/shows endpoint."""

    def setUp(self):
        super().setUp()
        # Create admin user and token for authenticated requests
        with self._app.get_db().sessionmaker() as session:
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            user_id = admin.id
            session.commit()

        self.token = self._app.jwt_service.create_access_token({"user_id": user_id})

    def test_get_shows_empty(self):
        """Test GET /api/v1/shows with no shows.

        This tests the query at line 214 in shows.py:
        session.scalars(select(Show)).all()
        """
        response = self.fetch("/api/v1/shows")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("shows", response_body)
        self.assertEqual([], response_body["shows"])

    def test_get_shows_with_data(self):
        """Test GET /api/v1/shows with existing shows."""
        # Create test shows
        with self._app.get_db().sessionmaker() as session:
            show1 = Show(name="Show 1", script_mode=ShowScriptType.FULL)
            show2 = Show(name="Show 2", script_mode=ShowScriptType.FULL)
            session.add(show1)
            session.add(show2)
            session.flush()

            # Add scripts for each show
            script1 = Script(show_id=show1.id)
            script2 = Script(show_id=show2.id)
            session.add(script1)
            session.add(script2)
            session.flush()

            revision1 = ScriptRevision(
                script_id=script1.id, revision=1, description="Initial"
            )
            revision2 = ScriptRevision(
                script_id=script2.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.add(revision2)
            session.flush()

            script1.current_revision = revision1.id
            script2.current_revision = revision2.id
            session.commit()

        response = self.fetch("/api/v1/shows")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(2, len(response_body["shows"]))
        self.assertEqual("Show 1", response_body["shows"][0]["name"])
        self.assertEqual("Show 2", response_body["shows"][1]["name"])

    def test_create_show_with_script_mode(self):
        """Test POST /api/v1/show with script_mode."""
        response = self.fetch(
            "/api/v1/show",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "name": "Test Show",
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                    "script_mode": ShowScriptType.FULL.value,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify in database
        with self._app.get_db().sessionmaker() as session:
            show = session.scalar(select(Show).where(Show.name == "Test Show"))
            self.assertIsNotNone(show)
            self.assertEqual(ShowScriptType.FULL, show.script_mode)

    def test_create_show_missing_script_mode(self):
        """Test POST /api/v1/show fails without script_mode."""
        response = self.fetch(
            "/api/v1/show",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "name": "Test Show",
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                    # script_mode intentionally missing
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Script mode missing", response_body["message"])

    def test_create_show_invalid_script_mode(self):
        """Test POST /api/v1/show fails with invalid script_mode."""
        response = self.fetch(
            "/api/v1/show",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "name": "Test Show",
                    "start": "2025-01-01",
                    "end": "2025-12-31",
                    "script_mode": 999,  # Invalid value
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid script mode value", response_body["message"])


class TestShowDeletionController(DigiScriptTestCase):
    """Test suite for DELETE /api/v1/show endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            user_id = admin.id

            show_a = Show(name="Loaded Show", script_mode=ShowScriptType.FULL)
            session.add(show_a)
            session.flush()
            self.show_a_id = show_a.id

            script_a = Script(show_id=show_a.id)
            session.add(script_a)
            session.flush()

            revision_a = ScriptRevision(
                script_id=script_a.id, revision=1, description="Initial"
            )
            session.add(revision_a)
            session.flush()
            self.revision_a_id = revision_a.id

            script_a.current_revision = revision_a.id
            session.commit()

        self.token = self._app.jwt_service.create_access_token({"user_id": user_id})
        self._app.digi_settings.settings["current_show"].set_value(self.show_a_id)

    def _create_show(self, name="Target Show"):
        """Create a minimal show and return its id."""
        with self._app.get_db().sessionmaker() as session:
            show = Show(name=name, script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            show_id = show.id
            session.commit()
        return show_id

    def _delete(self, show_id=None, token=None):
        """Issue DELETE /api/v1/show with optional id query param."""
        url = "/api/v1/show"
        if show_id is not None:
            url = f"{url}?id={show_id}"
        headers = {"Authorization": f"Bearer {token or self.token}"}
        return self.fetch(
            url, method="DELETE", headers=headers, allow_nonstandard_methods=True
        )

    def test_delete_show_success(self):
        """Deleting a non-loaded show returns 200 and removes it from the DB."""
        show_b_id = self._create_show()

        response = self._delete(show_b_id)
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertIn("Successfully deleted show", body["message"])

        with self._app.get_db().sessionmaker() as session:
            self.assertIsNone(session.get(Show, show_b_id))
            self.assertIsNotNone(session.get(Show, self.show_a_id))

    def test_delete_show_with_full_data(self):
        """Deleting a show with all associated data cascades correctly.

        Includes multiple acts/scenes with linked-list pointers (first_scene_id,
        previous_act_id, previous_scene_id) and a past show session, which exercise
        the circular-FK and post_update paths that single-act/scene setups miss.

        :raises AssertionError: if any related record survives the deletion.
        """
        with self._app.get_db().sessionmaker() as session:
            show_b = Show(name="Full Show", script_mode=ShowScriptType.FULL)
            session.add(show_b)
            session.flush()
            show_b_id = show_b.id

            script = Script(show_id=show_b_id)
            session.add(script)
            session.flush()
            script_id = script.id

            revision = ScriptRevision(
                script_id=script_id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()
            revision_id = revision.id

            script.current_revision = revision_id

            # Two acts with a linked-list pointer (previous_act_id) — exercises the
            # CircularDependencyError path that a single act never triggers.
            act1 = Act(show_id=show_b_id, name="Act 1")
            session.add(act1)
            session.flush()
            act1_id = act1.id

            act2 = Act(show_id=show_b_id, name="Act 2", previous_act_id=act1_id)
            session.add(act2)
            session.flush()
            act2_id = act2.id

            show_b.first_act_id = act1_id

            # Two scenes per act with previous_scene_id linked-list pointers.
            scene1 = Scene(show_id=show_b_id, act_id=act1_id, name="Scene 1")
            session.add(scene1)
            session.flush()
            scene1_id = scene1.id

            scene2 = Scene(
                show_id=show_b_id,
                act_id=act1_id,
                name="Scene 2",
                previous_scene_id=scene1_id,
            )
            session.add(scene2)
            session.flush()
            scene2_id = scene2.id

            act1.first_scene_id = scene1_id

            character = Character(show_id=show_b_id, name="Character 1")
            session.add(character)
            session.flush()
            character_id = character.id

            char_group = CharacterGroup(show_id=show_b_id, name="Group 1")
            session.add(char_group)
            session.flush()
            char_group_id = char_group.id

            cue_type = CueType(show_id=show_b_id, prefix="LX", description="Lighting")
            session.add(cue_type)
            session.flush()
            cue_type_id = cue_type.id

            microphone = Microphone(show_id=show_b_id, name="Mic 1")
            session.add(microphone)
            session.flush()
            microphone_id = microphone.id

            # Past show session referencing the revision — exercises the ShowSession
            # cascade path that previously caused an IntegrityError.
            past_session = ShowSession(
                show_id=show_b_id, script_revision_id=revision_id
            )
            session.add(past_session)
            session.flush()
            past_session_id = past_session.id

            session.commit()

        response = self._delete(show_b_id)
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            self.assertIsNone(session.get(Show, show_b_id), "Show should be deleted")
            self.assertIsNone(
                session.get(Script, script_id), "Script should be cascade deleted"
            )
            self.assertIsNone(
                session.get(ScriptRevision, revision_id),
                "Revision should be cascade deleted",
            )
            self.assertIsNone(
                session.get(Act, act1_id), "Act 1 should be cascade deleted"
            )
            self.assertIsNone(
                session.get(Act, act2_id), "Act 2 should be cascade deleted"
            )
            self.assertIsNone(
                session.get(Scene, scene1_id), "Scene 1 should be cascade deleted"
            )
            self.assertIsNone(
                session.get(Scene, scene2_id), "Scene 2 should be cascade deleted"
            )
            self.assertIsNone(
                session.get(Character, character_id),
                "Character should be cascade deleted",
            )
            self.assertIsNone(
                session.get(CharacterGroup, char_group_id),
                "CharacterGroup should be cascade deleted",
            )
            self.assertIsNone(
                session.get(CueType, cue_type_id), "CueType should be cascade deleted"
            )
            self.assertIsNone(
                session.get(Microphone, microphone_id),
                "Microphone should be cascade deleted",
            )
            self.assertIsNone(
                session.get(ShowSession, past_session_id),
                "Past ShowSession should be cascade deleted",
            )
            self.assertIsNotNone(
                session.get(Show, self.show_a_id), "Loaded show must not be deleted"
            )

    def test_delete_currently_loaded_show(self):
        """Attempting to delete the currently loaded show returns 400."""
        response = self._delete(self.show_a_id)
        self.assertEqual(400, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertIn("Cannot delete the currently loaded show", body["message"])

    def test_delete_show_missing_id(self):
        """Omitting the id query param returns 400."""
        response = self._delete()
        self.assertEqual(400, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", body["message"])

    def test_delete_show_invalid_id(self):
        """Passing a non-integer id returns 400."""
        response = self._delete("notanumber")
        self.assertEqual(400, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid ID", body["message"])

    def test_delete_show_not_found(self):
        """Passing an id that does not exist returns 404."""
        response = self._delete(99999)
        self.assertEqual(404, response.code)

    def test_delete_show_no_show_loaded(self):
        """With no current show in settings, the endpoint returns 400."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        show_b_id = self._create_show()
        response = self._delete(show_b_id)
        self.assertEqual(400, response.code)

    def test_delete_show_with_live_session(self):
        """Deleting while a live session is active on the loaded show returns 409."""
        show_b_id = self._create_show()

        with self._app.get_db().sessionmaker() as session:
            show_session = ShowSession(
                show_id=self.show_a_id,
                script_revision_id=self.revision_a_id,
            )
            session.add(show_session)
            session.flush()
            show_session_id = show_session.id

            show_a = session.get(Show, self.show_a_id)
            show_a.current_session_id = show_session_id
            session.commit()

        response = self._delete(show_b_id)
        self.assertEqual(409, response.code)
