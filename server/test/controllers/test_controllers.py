"""Tests for the legacy-UI redirect controller in ``controllers.controllers``.

Covers the retired Vue 2 UI's ``/ui-old/`` redirect, kept so bookmarked or
kiosk-configured URLs still land on the equivalent current-UI page instead of
404ing, without being usable as an open redirect.
"""

from test.conftest import DigiScriptTestCase


class TestLegacyUIRedirect(DigiScriptTestCase):
    def test_ui_old_root_redirects_to_root(self):
        response = self.fetch("/ui-old/", follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertEqual("/", response.headers["Location"])

    def test_ui_old_sub_path_redirects_to_equivalent_path(self):
        response = self.fetch("/ui-old/show/config", follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertEqual("/show/config", response.headers["Location"])

    def test_ui_old_with_switch_query_still_redirects(self):
        response = self.fetch("/ui-old/?_switch=1", follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertEqual("/", response.headers["Location"])

    def test_ui_old_double_slash_does_not_redirect_off_host(self):
        """``/ui-old//evil.com`` must not become a protocol-relative ``//evil.com``."""
        response = self.fetch("/ui-old//evil.com", follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertEqual("/evil.com", response.headers["Location"])

    def test_ui_old_backslash_does_not_redirect_off_host(self):
        """A leading backslash (``%5C``) is normalised by browsers to ``/``, so a
        bare ``\\evil.com`` target would behave like the double-slash case above.
        """
        response = self.fetch("/ui-old/%5Cevil.com", follow_redirects=False)
        self.assertEqual(302, response.code)
        self.assertEqual("/evil.com", response.headers["Location"])
