import json

from test.conftest import DigiScriptTestCase


class TestLoggingSettingDefaults(DigiScriptTestCase):
    def test_log_level_defaults_to_info(self):
        self.assertEqual("INFO", self._app.digi_settings.settings["log_level"].default)

    def test_log_redaction_enabled_by_default(self):
        setting = self._app.digi_settings.settings["log_redaction"]
        self.assertTrue(setting.default)
        self.assertTrue(setting.get_value())


class TestSavedLoggingSettingsAreKept(DigiScriptTestCase):
    """A value already saved in the settings file wins over a changed default."""

    def get_app(self):
        with open(self.settings_path, encoding="UTF-8") as file_pointer:
            saved = json.load(file_pointer)
        saved["log_redaction"] = False
        saved["log_level"] = "DEBUG"
        with open(self.settings_path, "w", encoding="UTF-8") as file_pointer:
            json.dump(saved, file_pointer)
        return super().get_app()

    def test_saved_log_redaction_is_not_overridden(self):
        setting = self._app.digi_settings.settings["log_redaction"]
        self.assertFalse(setting.get_value())

    def test_saved_log_level_is_not_overridden(self):
        setting = self._app.digi_settings.settings["log_level"]
        self.assertEqual("DEBUG", setting.get_value())
