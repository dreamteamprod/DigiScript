"""Tests for /api/v1/user/settings/cue_colour_overrides endpoints."""

import tornado.escape
from sqlalchemy import select

from models.cue import CueType
from models.show import Show
from models.user import User, UserOverrides
from test.conftest import DigiScriptTestCase


class TestCueColourOverridesController(DigiScriptTestCase):
    """Test suite for /api/v1/user/settings/cue_colour_overrides endpoints."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            # Create user for authentication
            user = User(username="testuser", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            # Create show
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create cue type
            cue_type = CueType(
                show_id=show.id,
                prefix="LX",
                description="Lighting",
                colour="#FF0000",
            )
            session.add(cue_type)
            session.flush()
            self.cue_type_id = cue_type.id

            # Create user override for testing
            override = UserOverrides(
                user_id=user.id,
                settings_type="cuetypes",
                settings='{"id": ' + str(self.cue_type_id) + ', "colour": "#0000FF"}',
            )
            session.add(override)
            session.flush()
            self.override_id = override.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_cue_colour_overrides(self):
        """Test GET /api/v1/user/settings/cue_colour_overrides.

        When a user has overrides for cue colours, the endpoint should return them.
        """
        # Create JWT token for authentication
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Get overrides
        response = self.fetch(
            "/api/v1/user/settings/cue_colour_overrides",
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify the response
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("overrides", response_body)
        self.assertEqual(1, len(response_body["overrides"]))
        self.assertEqual(self.override_id, response_body["overrides"][0]["id"])
        self.assertEqual("#0000FF", response_body["overrides"][0]["settings"]["colour"])

    def test_get_cue_colour_overrides_no_overrides(self):
        """Test GET when user has no overrides."""
        # Create a new user with no overrides
        with self._app.get_db().sessionmaker() as session:
            new_user = User(username="newuser", password="hashed", is_admin=False)
            session.add(new_user)
            session.commit()
            new_user_id = new_user.id

        # Create JWT token for the new user
        token = self._app.jwt_service.create_access_token(data={"user_id": new_user_id})

        # Get overrides - should return empty list
        response = self.fetch(
            "/api/v1/user/settings/cue_colour_overrides",
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify empty response
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("overrides", response_body)
        self.assertEqual(0, len(response_body["overrides"]))

    def test_post_cue_colour_override(self):
        """Test POST /api/v1/user/settings/cue_colour_overrides."""
        # Create another cue type
        with self._app.get_db().sessionmaker() as session:
            cue_type = CueType(
                show_id=self.show_id,
                prefix="SND",
                description="Sound",
                colour="#00FF00",
            )
            session.add(cue_type)
            session.commit()
            new_cue_type_id = cue_type.id

        # Create JWT token
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Create new override
        response = self.fetch(
            "/api/v1/user/settings/cue_colour_overrides",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode(
                {
                    "cueTypeId": new_cue_type_id,
                    "colour": "#FFFF00",
                }
            ),
        )

        # Verify response
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("id", response_body)
        self.assertIn("message", response_body)

        # Verify override was created in database
        with self._app.get_db().sessionmaker() as session:
            override = session.get(UserOverrides, response_body["id"])
            self.assertIsNotNone(override)
            self.assertEqual(self.user_id, override.user_id)
            self.assertEqual("cuetypes", override.settings_type)
            settings = override.settings_dict
            self.assertEqual(new_cue_type_id, settings["id"])
            self.assertEqual("#FFFF00", settings["colour"])

    def test_post_cue_colour_override_missing_cue_type_id(self):
        """Test POST with missing cueTypeId returns 400."""
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        response = self.fetch(
            "/api/v1/user/settings/cue_colour_overrides",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode({"colour": "#FFFF00"}),
        )

        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("message", response_body)
        self.assertIn("missing", response_body["message"].lower())

    def test_post_cue_colour_override_missing_colour(self):
        """Test POST with missing colour returns 400."""
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        response = self.fetch(
            "/api/v1/user/settings/cue_colour_overrides",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode({"cueTypeId": self.cue_type_id}),
        )

        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("message", response_body)
        self.assertIn("colour", response_body["message"].lower())

    def test_post_cue_colour_override_invalid_cue_type(self):
        """Test POST with non-existent cue type returns 404."""
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        response = self.fetch(
            "/api/v1/user/settings/cue_colour_overrides",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode(
                {
                    "cueTypeId": 99999,  # Non-existent
                    "colour": "#FFFF00",
                }
            ),
        )

        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("message", response_body)

    def test_patch_cue_colour_override(self):
        """Test PATCH /api/v1/user/settings/cue_colour_overrides."""
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Update existing override
        response = self.fetch(
            "/api/v1/user/settings/cue_colour_overrides",
            method="PATCH",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode(
                {
                    "id": self.override_id,
                    "colour": "#00FFFF",
                }
            ),
        )

        # Verify response
        self.assertEqual(200, response.code)

        # Verify override was updated in database
        with self._app.get_db().sessionmaker() as session:
            override = session.get(UserOverrides, self.override_id)
            settings = override.settings_dict
            self.assertEqual("#00FFFF", settings["colour"])

    def test_patch_cue_colour_override_not_owned(self):
        """Test PATCH for override owned by another user returns 403."""
        # Create another user
        with self._app.get_db().sessionmaker() as session:
            other_user = User(username="otheruser", password="hashed", is_admin=False)
            session.add(other_user)
            session.commit()
            other_user_id = other_user.id

        # Try to update original user's override
        token = self._app.jwt_service.create_access_token(
            data={"user_id": other_user_id}
        )

        response = self.fetch(
            "/api/v1/user/settings/cue_colour_overrides",
            method="PATCH",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode(
                {
                    "id": self.override_id,
                    "colour": "#00FFFF",
                }
            ),
        )

        self.assertEqual(403, response.code)

    def test_delete_cue_colour_override(self):
        """Test DELETE /api/v1/user/settings/cue_colour_overrides."""
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Delete override
        response = self.fetch(
            f"/api/v1/user/settings/cue_colour_overrides?id={self.override_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify response
        self.assertEqual(200, response.code)

        # Verify override was deleted from database
        with self._app.get_db().sessionmaker() as session:
            override = session.get(UserOverrides, self.override_id)
            self.assertIsNone(override)

    def test_delete_cue_colour_override_not_owned(self):
        """Test DELETE for override owned by another user returns 403."""
        # Create another user
        with self._app.get_db().sessionmaker() as session:
            other_user = User(username="otheruser", password="hashed", is_admin=False)
            session.add(other_user)
            session.commit()
            other_user_id = other_user.id

        # Try to delete original user's override
        token = self._app.jwt_service.create_access_token(
            data={"user_id": other_user_id}
        )

        response = self.fetch(
            f"/api/v1/user/settings/cue_colour_overrides?id={self.override_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(403, response.code)

    def test_cascade_delete_cue_type_deletes_overrides(self):
        """Test that deleting a cue type cascades to delete user overrides."""
        # Verify override exists
        with self._app.get_db().sessionmaker() as session:
            override = session.get(UserOverrides, self.override_id)
            self.assertIsNotNone(override)

        # Delete the cue type
        with self._app.get_db().sessionmaker() as session:
            cue_type = session.get(CueType, self.cue_type_id)
            session.delete(cue_type)
            session.commit()

        # Verify override was cascade deleted
        with self._app.get_db().sessionmaker() as session:
            override = session.get(UserOverrides, self.override_id)
            self.assertIsNone(override)
