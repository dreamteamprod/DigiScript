"""Tests for the security hygiene hardening: JSON body parsing, admin status codes,
RBAC input validation, user settings allow-list and default security headers."""

from tornado import escape

from models.user import UserSettings
from test.conftest import DigiScriptTestCase


class TestSecurityHygiene(DigiScriptTestCase):
    def _auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def _post(self, path, body, token=None, method="POST"):
        return self.fetch(
            path,
            method=method,
            body=body if isinstance(body, str) else escape.json_encode(body),
            headers=self._auth(token) if token else {},
            raise_error=False,
        )

    # ─── Security headers ──────────────────────────────────────────────────────

    def test_security_headers_present(self):
        resp = self.fetch("/api/v1/health", raise_error=False)
        self.assertEqual("nosniff", resp.headers.get("X-Content-Type-Options"))
        self.assertEqual("SAMEORIGIN", resp.headers.get("X-Frame-Options"))
        self.assertEqual("same-origin", resp.headers.get("Referrer-Policy"))

    def test_security_headers_present_on_error_responses(self):
        resp = self.fetch("/api/v1/rbac/user/resources", raise_error=False)
        self.assertEqual(401, resp.code)
        self.assertEqual("nosniff", resp.headers.get("X-Content-Type-Options"))

    # ─── JSON body helper ──────────────────────────────────────────────────────

    def test_login_invalid_json_returns_400(self):
        self.assertEqual(400, self._post("/api/v1/auth/login", "{not json").code)

    def test_login_non_object_json_returns_400(self):
        self.assertEqual(400, self._post("/api/v1/auth/login", "[1, 2]").code)

    def test_login_empty_body_returns_400(self):
        self.assertEqual(400, self._post("/api/v1/auth/login", "").code)

    def test_create_user_invalid_json_returns_400(self):
        self.assertEqual(400, self._post("/api/v1/auth/create", "nope").code)

    def test_v2_create_user_invalid_json_returns_400(self):
        self.assertEqual(400, self._post("/api/v2/users", "nope").code)

    def test_change_password_invalid_json_returns_400(self):
        token = self._create_and_login_admin()
        resp = self._post("/api/v1/auth/change-password", "nope", token, "PATCH")
        self.assertEqual(400, resp.code)

    def test_rbac_grant_invalid_json_returns_400(self):
        token = self._create_and_login_admin()
        self.assertEqual(
            400, self._post("/api/v1/rbac/user/roles/grant", "nope", token).code
        )

    def test_user_settings_patch_non_object_returns_400(self):
        token = self._create_and_login_admin()
        resp = self._post("/api/v1/user/settings", "[1]", token, "PATCH")
        self.assertEqual(400, resp.code)

    def test_system_settings_patch_invalid_json_returns_400(self):
        token = self._create_and_login_admin()
        resp = self._post("/api/v1/settings", "nope", token, "PATCH")
        self.assertEqual(400, resp.code)

    def test_session_start_invalid_json_returns_400(self):
        token = self._create_and_login_admin()
        resp = self._post("/api/v1/show/sessions/start", "nope", token)
        # No show is loaded in this fixture, so requires_show answers first.
        self.assertEqual(400, resp.code)

    # ─── require_admin status codes ────────────────────────────────────────────

    def test_require_admin_unauthenticated_is_401(self):
        resp = self._post("/api/v1/rbac/user/roles/grant", {})
        self.assertEqual(401, resp.code)

    def test_require_admin_non_admin_is_403(self):
        admin_token = self._create_and_login_admin()
        user_token = self._create_and_login_user(admin_token)
        resp = self._post("/api/v1/rbac/user/roles/grant", {}, user_token)
        self.assertEqual(403, resp.code)

    # ─── RBAC grant / revoke validation ────────────────────────────────────────

    def _role_body(self, **overrides):
        body = {
            "resource": "shows",
            "object": {"id": 1},
            "user": 1,
            "role": 1,
        }
        body.update(overrides)
        return body

    def test_rbac_grant_and_revoke_invalid_input_returns_400(self):
        token = self._create_and_login_admin()
        bad_bodies = [
            self._role_body(role=999999),
            self._role_body(role="admin"),
            self._role_body(user="abc"),
            self._role_body(object="not-a-dict"),
            self._role_body(object={"unrelated": 1}),
            self._role_body(resource=["shows"]),
        ]
        for path in (
            "/api/v1/rbac/user/roles/grant",
            "/api/v1/rbac/user/roles/revoke",
        ):
            for body in bad_bodies:
                with self.subTest(path=path, body=body):
                    resp = self._post(path, body, token)
                    self.assertEqual(400, resp.code)

    def test_rbac_grant_missing_field_returns_400(self):
        token = self._create_and_login_admin()
        body = self._role_body()
        del body["role"]
        resp = self._post("/api/v1/rbac/user/roles/grant", body, token)
        self.assertEqual(400, resp.code)

    # ─── User settings allow-list ──────────────────────────────────────────────

    def test_user_settings_patch_sets_allowed_and_ignores_others(self):
        token = self._create_and_login_admin()
        resp = self._post(
            "/api/v1/user/settings",
            {
                "cue_position_right": True,
                "_user_id": 999,
                "metadata": "x",
                "registry": "x",
                "nonexistent": 1,
            },
            token,
            "PATCH",
        )
        self.assertEqual(200, resp.code)

        with self._app.get_db().sessionmaker() as session:
            settings = session.scalars(session.query(UserSettings).statement).first()
            self.assertTrue(settings.cue_position_right)
            self.assertNotEqual(999, settings._user_id)
