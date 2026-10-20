from test.conftest import DigiScriptTestCase


class TestLoggingSettingDefaults(DigiScriptTestCase):
    def test_log_level_defaults_to_info(self):
        self.assertEqual("INFO", self._app.digi_settings.settings["log_level"].default)

    def test_log_redaction_enabled_by_default(self):
        setting = self._app.digi_settings.settings["log_redaction"]
        self.assertTrue(setting.default)
        self.assertTrue(setting.get_value())
