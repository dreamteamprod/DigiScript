from tornado.testing import gen_test

from digi_server.logger import get_logger

from test.utils import DigiScriptTestCase


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
