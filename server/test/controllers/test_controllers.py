"""Tests for the root-level controllers in ``controllers.controllers``.

Covers the retired Vue 2 UI's ``/ui-old/`` redirect, kept so bookmarked or
kiosk-configured URLs still land on the current UI instead of 404ing.
"""

from test.conftest import DigiScriptTestCase


class TestLegacyUIRedirect(DigiScriptTestCase):
    def test_ui_old_root_redirects_to_root(self):
        response = self.fetch("/ui-old/", follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertEqual("/", response.headers["Location"])

    def test_ui_old_sub_path_redirects_to_root(self):
        response = self.fetch("/ui-old/show/config", follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertEqual("/", response.headers["Location"])

    def test_ui_old_with_switch_query_still_redirects(self):
        response = self.fetch("/ui-old/?_switch=1", follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertEqual("/", response.headers["Location"])
