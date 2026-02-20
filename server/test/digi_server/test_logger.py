import logging
import unittest

from digi_server.logger import CLIENT_LEVEL_MAP, map_client_level


class TestMapClientLevel(unittest.TestCase):
    def test_trace_maps_to_level_5(self):
        self.assertEqual(5, map_client_level("TRACE"))

    def test_debug_maps_to_logging_debug(self):
        self.assertEqual(logging.DEBUG, map_client_level("DEBUG"))

    def test_info_maps_to_logging_info(self):
        self.assertEqual(logging.INFO, map_client_level("INFO"))

    def test_warn_maps_to_logging_warning(self):
        """loglevel npm uses WARN; Python uses WARNING (30)."""
        self.assertEqual(logging.WARNING, map_client_level("WARN"))

    def test_error_maps_to_logging_error(self):
        self.assertEqual(logging.ERROR, map_client_level("ERROR"))

    def test_silent_maps_above_critical(self):
        """SILENT has no Python equivalent; should suppress all output."""
        self.assertEqual(logging.CRITICAL + 1, map_client_level("SILENT"))

    def test_unknown_level_falls_back_to_info(self):
        self.assertEqual(logging.INFO, map_client_level("UNKNOWN"))
        self.assertEqual(logging.INFO, map_client_level(""))
        self.assertEqual(logging.INFO, map_client_level("NOTSET"))

    def test_case_insensitive(self):
        self.assertEqual(logging.WARNING, map_client_level("warn"))
        self.assertEqual(logging.INFO, map_client_level("info"))
        self.assertEqual(5, map_client_level("trace"))

    def test_client_level_map_contains_all_expected_keys(self):
        expected = {"TRACE", "DEBUG", "INFO", "WARN", "ERROR", "SILENT"}
        self.assertEqual(expected, set(CLIENT_LEVEL_MAP.keys()))
