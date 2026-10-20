import pytest
from tornado import escape
from tornado.testing import gen_test

from digi_server.logger import get_logger
from test.conftest import DigiScriptTestCase


class TestSettings(DigiScriptTestCase):
    @gen_test
    def test_set_invalid_name(self):
        yield self._app.digi_settings.set("not_present_key", "some_value")
        self.assertLogs(
            get_logger(),
            "Setting not_present_key found in settings file is not defined, ignoring!",
        )

    @gen_test
    def test_get_invalid_name(self):
        with self.assertRaises(KeyError):
            yield self._app.digi_settings.get("not_present_key")

    @gen_test
    def test_get_set_valid_name(self):
        cur_val = yield self._app.digi_settings.get("debug_mode")
        self.assertEqual(False, cur_val)

        yield self._app.digi_settings.set("debug_mode", True)
        cur_val = yield self._app.digi_settings.get("debug_mode")
        self.assertEqual(True, cur_val)

    @gen_test
    def test_invalid_type(self):
        with self.assertRaises(TypeError):
            yield self._app.digi_settings.set("debug_mode", "not_a_bool")

    @gen_test
    def test_not_nullable(self):
        with self.assertRaises(RuntimeError):
            yield self._app.digi_settings.set("debug_mode", None)

    def test_jwt_lifetime_setting_registered(self):
        setting = self._app.digi_settings.settings.get("jwt_token_lifetime_hours")
        self.assertIsNotNone(setting)
        self.assertEqual(setting.default, 24)
        self.assertEqual(setting.val_type, int)
        self.assertEqual(setting.choice_options, [1, 6, 12, 24, 168, 720])
        self.assertIsNotNone(setting.choice_labels)
        self.assertEqual(len(setting.choice_labels), len(setting.choice_options))
        self.assertTrue(setting.can_edit)

    def test_jwt_lifetime_setting_rejects_invalid_choice(self):
        with pytest.raises(ValueError):
            self._app.digi_settings.settings["jwt_token_lifetime_hours"].set_value(999)

    def test_jwt_lifetime_setting_in_security_category(self):
        categories = self._app.digi_settings.categories
        self.assertIn("Security", categories)
        self.assertIn("jwt_token_lifetime_hours", categories["Security"])

    def test_jwt_lifetime_as_json_includes_choice_labels(self):
        setting = self._app.digi_settings.settings["jwt_token_lifetime_hours"]
        json_repr = setting.as_json()
        self.assertIn("choice_labels", json_repr)
        self.assertEqual(
            len(json_repr["choice_labels"]), len(json_repr["choice_options"])
        )


class TestSettingsDisclosure(DigiScriptTestCase):
    PATH_KEYS = (
        "db_path",
        "log_path",
        "db_log_path",
        "client_log_path",
        "compiled_script_path",
        "draft_script_path",
    )

    def _get(self, path, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return escape.json_decode(self.fetch(path, headers=headers).body)

    def test_settings_hide_paths_from_anonymous(self):
        for path in ("/api/v1/settings", "/api/v1/settings/raw"):
            data = self._get(path)
            for key in self.PATH_KEYS:
                self.assertNotIn(key, data)
            self.assertIn("client_log_enabled", data)

    def test_settings_hide_paths_from_non_admin(self):
        admin = self._create_and_login_admin()
        user = self._create_and_login_user(admin)
        for path in ("/api/v1/settings", "/api/v1/settings/raw"):
            data = self._get(path, user)
            for key in self.PATH_KEYS:
                self.assertNotIn(key, data)

    def test_settings_show_paths_to_admin(self):
        admin = self._create_and_login_admin()
        for path in ("/api/v1/settings", "/api/v1/settings/raw"):
            data = self._get(path, admin)
            for key in self.PATH_KEYS:
                self.assertIn(key, data)

    def test_broadcast_payload_has_no_paths(self):
        data = self.io_loop.run_sync(self._app.digi_settings.as_json)
        for key in self.PATH_KEYS:
            self.assertNotIn(key, data)


class TestSettingsController(DigiScriptTestCase):
    def test_patch_invalid_json_returns_400(self):
        token = self._create_and_login_admin()
        resp = self.fetch(
            "/api/v1/settings",
            method="PATCH",
            body="nope",
            headers={"Authorization": f"Bearer {token}"},
            raise_error=False,
        )
        self.assertEqual(400, resp.code)
