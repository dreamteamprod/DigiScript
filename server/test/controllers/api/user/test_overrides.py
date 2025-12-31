"""Tests for /api/v1/user/settings/stage_direction_overrides endpoints."""

import pytest
import tornado.escape
from sqlalchemy import select

from models.cue import CueType
from models.script import Script, StageDirectionStyle
from models.show import Show, ShowScriptType
from models.user import User, UserOverrides
from test.conftest import DigiScriptTestCase


class TestStageDirectionOverridesController(DigiScriptTestCase):
    """Test suite for /api/v1/user/settings/stage_direction_overrides endpoints."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            # Create user for authentication
            user = User(username="testuser", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            # Create show (required by some decorators)
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create script
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            # Create stage direction style
            style = StageDirectionStyle(
                script_id=script.id,
                description="Test Style",
                bold=True,
                text_colour="#FF0000",
            )
            session.add(style)
            session.flush()
            self.style_id = style.id

            # Create user override for testing - must include all required fields
            override = UserOverrides(
                user_id=user.id,
                settings_type="stage_direction_styles",
                settings='{"id": '
                + str(self.style_id)
                + ', "bold": true, "italic": false, "underline": false, '
                + '"text_format": "upper", "text_colour": "#FF0000", '
                + '"enable_background_colour": true, "background_colour": "#FFFF00"}',
            )
            session.add(override)
            session.flush()
            self.override_id = override.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_stage_direction_overrides(self):
        """Test GET /api/v1/user/settings/stage_direction_overrides.

        This tests the query at lines 99-103 in models/user.py:
        session.scalars(
            select(UserOverrides)
            .where(UserOverrides.user_id == user_id)
            .where(UserOverrides.settings_type == settings_type)
        ).all()

        When a user has overrides for stage direction styles, the endpoint should
        return them.
        """
        # Create JWT token for authentication
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Get overrides - this triggers the query
        response = self.fetch(
            "/api/v1/user/settings/stage_direction_overrides",
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify the response
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("overrides", response_body)
        self.assertEqual(1, len(response_body["overrides"]))
        self.assertEqual(self.override_id, response_body["overrides"][0]["id"])
        # Verify all override fields are present
        settings = response_body["overrides"][0]["settings"]
        self.assertEqual(True, settings["bold"])
        self.assertEqual(False, settings["italic"])
        self.assertEqual("upper", settings["text_format"])
        self.assertEqual("#FF0000", settings["text_colour"])

    def test_get_stage_direction_overrides_no_overrides(self):
        """Test GET when user has no overrides.

        This tests the same query but with an empty result set.
        """
        # Create a new user with no overrides
        with self._app.get_db().sessionmaker() as session:
            new_user = User(username="newuser", password="hashed", is_admin=False)
            session.add(new_user)
            session.commit()
            new_user_id = new_user.id

        # Create JWT token for the new user
        token = self._app.jwt_service.create_access_token(data={"user_id": new_user_id})

        # Get overrides - query should return empty list
        response = self.fetch(
            "/api/v1/user/settings/stage_direction_overrides",
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify empty response
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("overrides", response_body)
        self.assertEqual(0, len(response_body["overrides"]))

    def test_post_stage_direction_override(self):
        """Test POST /api/v1/user/settings/stage_direction_overrides."""
        # Create another stage direction style
        with self._app.get_db().sessionmaker() as session:
            script = session.get(Script, session.scalars(select(Script)).first().id)
            style = StageDirectionStyle(
                script_id=script.id,
                description="Asides",
                bold=False,
                italic=True,
                underline=False,
                text_format="default",
                text_colour="#666666",
                enable_background_colour=False,
                background_colour="#FFFFFF",
            )
            session.add(style)
            session.commit()
            new_style_id = style.id

        # Create JWT token
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Create new override
        response = self.fetch(
            "/api/v1/user/settings/stage_direction_overrides",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode(
                {
                    "styleId": new_style_id,
                    "bold": True,
                    "italic": False,
                    "underline": True,
                    "textFormat": "lower",
                    "textColour": "#0000FF",
                    "enableBackgroundColour": True,
                    "backgroundColour": "#CCCCCC",
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
            self.assertEqual("stage_direction_styles", override.settings_type)
            settings = override.settings_dict
            self.assertEqual(new_style_id, settings["id"])
            self.assertEqual(True, settings["bold"])
            self.assertEqual(False, settings["italic"])
            self.assertEqual(True, settings["underline"])
            self.assertEqual("lower", settings["text_format"])
            self.assertEqual("#0000FF", settings["text_colour"])
            self.assertEqual(True, settings["enable_background_colour"])
            self.assertEqual("#CCCCCC", settings["background_colour"])

    def test_post_stage_direction_override_validation_errors(self):
        """Test POST with various invalid payloads returns appropriate errors."""
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Define test cases: (name, payload, expected_status, expected_message)
        test_cases = [
            (
                "missing_style_id",
                {
                    "bold": True,
                    "italic": False,
                    "underline": False,
                    "textFormat": "default",
                    "textColour": "#000000",
                    "enableBackgroundColour": False,
                },
                400,
                "missing",
            ),
            (
                "missing_text_format",
                {
                    "styleId": self.style_id,
                    "bold": True,
                    "italic": False,
                    "underline": False,
                    "textColour": "#000000",
                    "enableBackgroundColour": False,
                },
                400,
                "text format",
            ),
            (
                "invalid_text_format",
                {
                    "styleId": self.style_id,
                    "bold": True,
                    "italic": False,
                    "underline": False,
                    "textFormat": "invalid",
                    "textColour": "#000000",
                    "enableBackgroundColour": False,
                },
                400,
                "text format",
            ),
            (
                "missing_text_colour",
                {
                    "styleId": self.style_id,
                    "bold": True,
                    "italic": False,
                    "underline": False,
                    "textFormat": "default",
                    "enableBackgroundColour": False,
                },
                400,
                "text colour",
            ),
            (
                "missing_background_colour_when_enabled",
                {
                    "styleId": self.style_id,
                    "bold": True,
                    "italic": False,
                    "underline": False,
                    "textFormat": "default",
                    "textColour": "#000000",
                    "enableBackgroundColour": True,
                },
                400,
                "background colour",
            ),
        ]

        for name, payload, expected_status, expected_message in test_cases:
            with self.subTest(test_case=name):
                response = self.fetch(
                    "/api/v1/user/settings/stage_direction_overrides",
                    method="POST",
                    headers={"Authorization": f"Bearer {token}"},
                    body=tornado.escape.json_encode(payload),
                )

                self.assertEqual(expected_status, response.code)
                response_body = tornado.escape.json_decode(response.body)
                self.assertIn("message", response_body)
                self.assertIn(expected_message, response_body["message"].lower())

    def test_post_stage_direction_override_invalid_style_id(self):
        """Test POST with non-existent style ID returns 404."""
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        response = self.fetch(
            "/api/v1/user/settings/stage_direction_overrides",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode(
                {
                    "styleId": 99999,  # Non-existent
                    "bold": True,
                    "italic": False,
                    "underline": False,
                    "textFormat": "default",
                    "textColour": "#000000",
                    "enableBackgroundColour": False,
                }
            ),
        )

        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("message", response_body)
        self.assertIn("not found", response_body["message"].lower())

    def test_patch_stage_direction_override(self):
        """Test PATCH /api/v1/user/settings/stage_direction_overrides."""
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Update existing override - use snake_case field names
        response = self.fetch(
            "/api/v1/user/settings/stage_direction_overrides",
            method="PATCH",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode(
                {
                    "id": self.override_id,
                    "bold": False,
                    "italic": True,
                    "text_colour": "#00FF00",
                }
            ),
        )

        # Verify response
        self.assertEqual(200, response.code)

        # Verify override was updated in database
        with self._app.get_db().sessionmaker() as session:
            override = session.get(UserOverrides, self.override_id)
            settings = override.settings_dict
            self.assertEqual(False, settings["bold"])
            self.assertEqual(True, settings["italic"])
            self.assertEqual("#00FF00", settings["text_colour"])

    def test_patch_stage_direction_override_not_owned(self):
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
            "/api/v1/user/settings/stage_direction_overrides",
            method="PATCH",
            headers={"Authorization": f"Bearer {token}"},
            body=tornado.escape.json_encode(
                {
                    "id": self.override_id,
                    "bold": False,
                    "text_colour": "#00FF00",
                }
            ),
        )

        self.assertEqual(403, response.code)

    def test_delete_stage_direction_override(self):
        """Test DELETE /api/v1/user/settings/stage_direction_overrides."""
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Delete override
        response = self.fetch(
            f"/api/v1/user/settings/stage_direction_overrides?id={self.override_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify response
        self.assertEqual(200, response.code)

        # Verify override was deleted from database
        with self._app.get_db().sessionmaker() as session:
            override = session.get(UserOverrides, self.override_id)
            self.assertIsNone(override)

    def test_delete_stage_direction_override_not_owned(self):
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
            f"/api/v1/user/settings/stage_direction_overrides?id={self.override_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(403, response.code)

    def test_cascade_delete_stage_direction_style_deletes_overrides(self):
        """Test that deleting a stage direction style cascades to delete user overrides."""
        # Verify override exists
        with self._app.get_db().sessionmaker() as session:
            override = session.get(UserOverrides, self.override_id)
            self.assertIsNotNone(override)

        # Delete the stage direction style
        with self._app.get_db().sessionmaker() as session:
            style = session.get(StageDirectionStyle, self.style_id)
            session.delete(style)
            session.commit()

        # Verify override was cascade deleted
        with self._app.get_db().sessionmaker() as session:
            override = session.get(UserOverrides, self.override_id)
            self.assertIsNone(override)


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
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
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
