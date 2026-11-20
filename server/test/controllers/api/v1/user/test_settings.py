"""Tests for the /api/v1/user/settings controller."""

from unittest.mock import patch

from sqlalchemy import select
from tornado import escape

from models.user import User, UserSettings
from test.conftest import DigiScriptTestCase


class TestUserSettingsController(DigiScriptTestCase):
    def _patch(self, body, token):
        return self.fetch(
            "/api/v1/user/settings",
            method="PATCH",
            body=body if isinstance(body, str) else escape.json_encode(body),
            headers={"Authorization": f"Bearer {token}"},
            raise_error=False,
        )

    def test_patch_non_object_returns_400(self):
        token = self._create_and_login_admin()
        self.assertEqual(400, self._patch("[1]", token).code)

    def test_patch_invalid_json_returns_400(self):
        token = self._create_and_login_admin()
        self.assertEqual(400, self._patch("nope", token).code)

    def test_patch_sets_allowed_and_ignores_others(self):
        token = self._create_and_login_admin()
        # Create the settings row first so its constructor is not recorded below.
        self.fetch(
            "/api/v1/user/settings", headers={"Authorization": f"Bearer {token}"}
        )
        assigned = []
        original_setattr = UserSettings.__setattr__

        def recording_setattr(obj, name, value):
            assigned.append(name)
            original_setattr(obj, name, value)

        with patch.object(UserSettings, "__setattr__", recording_setattr):
            resp = self._patch(
                {
                    "cue_position_right": True,
                    "_user_id": 999,
                    "metadata": "x",
                    "registry": "x",
                    "nonexistent": 1,
                },
                token,
            )
        self.assertEqual(200, resp.code)

        # Only the allow-listed field is ever assigned; existing non-column
        # attributes (metadata, registry) and protected/unknown keys are skipped.
        for name in ("metadata", "registry", "_user_id", "nonexistent"):
            self.assertNotIn(name, assigned)
        self.assertIn("cue_position_right", assigned)

        with self._app.get_db().sessionmaker() as session:
            admin = session.scalars(select(User).where(User.username == "admin")).one()
            settings = session.get(UserSettings, admin.id)
            self.assertTrue(settings.cue_position_right)
