"""Tests for /api/v1/user/settings/stage_direction_overrides endpoints."""

import tornado.escape
from sqlalchemy import select

from models.script import Script, StageDirectionStyle
from models.show import Show
from models.user import User, UserOverrides
from test.utils import DigiScriptTestCase


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
            show = Show(name="Test Show")
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

            # Create user override for testing
            override = UserOverrides(
                user_id=user.id,
                settings_type="stage_direction_styles",
                settings='{"id": "' + str(self.style_id) + '", "bold": true}',
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
