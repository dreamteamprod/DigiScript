import pytest
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
