"""Tests for the /api/v1/user/settings controller."""

from tornado import escape

from models.user import UserSettings
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

        with self._app.get_db().sessionmaker() as session:
            settings = session.scalars(session.query(UserSettings).statement).first()
            self.assertTrue(settings.cue_position_right)
            self.assertNotEqual(999, settings._user_id)
