from prometheus_client import REGISTRY
from sqlalchemy import select
from tornado import escape

from models.user import User
from test.conftest import DigiScriptTestCase


class TestUsersV2Controller(DigiScriptTestCase):
    """Tests for GET/POST/PATCH/DELETE /api/v2/users"""

    def _setup_admin(self, username="admin", password="adminpass"):
        self.fetch(
            "/api/v2/users",
            method="POST",
            body=escape.json_encode(
                {"username": username, "password": password, "is_admin": True}
            ),
        )
        resp = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": username, "password": password}),
        )
        return escape.json_decode(resp.body)["access_token"]

    def _create_user(
        self, admin_token, username="user", password="userpass", is_admin=False
    ):
        resp = self.fetch(
            "/api/v2/users",
            method="POST",
            body=escape.json_encode(
                {"username": username, "password": password, "is_admin": is_admin}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(200, resp.code)
        with self._app.get_db().sessionmaker() as session:
            u = session.scalars(select(User).where(User.username == username)).first()
            return u.id

    # ─── GET /api/v2/users ─────────────────────────────────────────────────────

    def test_get_users_returns_all_users(self):
        admin_token = self._setup_admin()
        self._create_user(admin_token, username="user1")
        self._create_user(admin_token, username="user2")

        resp = self.fetch(
            "/api/v2/users",
            method="GET",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(200, resp.code)
        body = escape.json_decode(resp.body)
        self.assertIn("users", body)
        usernames = [u["username"] for u in body["users"]]
        self.assertIn("admin", usernames)
        self.assertIn("user1", usernames)
        self.assertIn("user2", usernames)

    def test_get_users_requires_admin(self):
        admin_token = self._setup_admin()
        self._create_user(admin_token, username="nonadmin")
        resp = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "nonadmin", "password": "userpass"}),
        )
        nonadmin_token = escape.json_decode(resp.body)["access_token"]

        resp = self.fetch(
            "/api/v2/users",
            method="GET",
            headers={"Authorization": f"Bearer {nonadmin_token}"},
        )
        self.assertEqual(403, resp.code)

    # ─── POST /api/v2/users ────────────────────────────────────────────────────

    def test_post_create_user_success(self):
        admin_token = self._setup_admin()
        resp = self.fetch(
            "/api/v2/users",
            method="POST",
            body=escape.json_encode(
                {"username": "newuser", "password": "password", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(200, resp.code)
        self.assertEqual(
            "Successfully created user", escape.json_decode(resp.body)["message"]
        )

    def test_post_first_user_must_be_admin(self):
        resp = self.fetch(
            "/api/v2/users",
            method="POST",
            body=escape.json_encode(
                {"username": "user", "password": "password", "is_admin": False}
            ),
        )
        self.assertEqual(400, resp.code)
        self.assertEqual(
            "First user must be an admin", escape.json_decode(resp.body)["message"]
        )

    def test_post_missing_username(self):
        resp = self.fetch(
            "/api/v2/users",
            method="POST",
            body=escape.json_encode({"password": "password", "is_admin": True}),
        )
        self.assertEqual(400, resp.code)
        self.assertEqual("Username missing", escape.json_decode(resp.body)["message"])

    def test_post_duplicate_username(self):
        admin_token = self._setup_admin()
        resp = self.fetch(
            "/api/v2/users",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "password", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(400, resp.code)
        self.assertEqual(
            "Username already taken", escape.json_decode(resp.body)["message"]
        )

    # ─── PATCH /api/v2/users?id={n} ───────────────────────────────────────────

    def test_patch_toggle_admin_success(self):
        admin_token = self._setup_admin()
        second_admin_id = self._create_user(
            admin_token, username="admin2", password="adminpass2", is_admin=True
        )

        resp = self.fetch(
            f"/api/v2/users?id={second_admin_id}",
            method="PATCH",
            body=escape.json_encode({"is_admin": False}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(200, resp.code)
        self.assertEqual(
            "Successfully updated user", escape.json_decode(resp.body)["message"]
        )

        with self._app.get_db().sessionmaker() as session:
            self.assertFalse(session.get(User, second_admin_id).is_admin)

    def test_patch_promote_user_to_admin(self):
        admin_token = self._setup_admin()
        user_id = self._create_user(admin_token)

        resp = self.fetch(
            f"/api/v2/users?id={user_id}",
            method="PATCH",
            body=escape.json_encode({"is_admin": True}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(200, resp.code)

        with self._app.get_db().sessionmaker() as session:
            self.assertTrue(session.get(User, user_id).is_admin)

    def test_patch_requires_admin(self):
        admin_token = self._setup_admin()
        user_id = self._create_user(admin_token)
        resp = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "user", "password": "userpass"}),
        )
        user_token = escape.json_decode(resp.body)["access_token"]

        resp = self.fetch(
            f"/api/v2/users?id={user_id}",
            method="PATCH",
            body=escape.json_encode({"is_admin": True}),
            headers={"Authorization": f"Bearer {user_token}"},
        )
        self.assertEqual(403, resp.code)

    def test_patch_missing_id(self):
        admin_token = self._setup_admin()
        resp = self.fetch(
            "/api/v2/users",
            method="PATCH",
            body=escape.json_encode({"is_admin": False}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(400, resp.code)
        self.assertEqual("Id missing", escape.json_decode(resp.body)["message"])

    def test_patch_user_not_found(self):
        admin_token = self._setup_admin()
        resp = self.fetch(
            "/api/v2/users?id=99999",
            method="PATCH",
            body=escape.json_encode({"is_admin": False}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(404, resp.code)
        self.assertEqual("User not found", escape.json_decode(resp.body)["message"])

    def test_patch_self_edit_rejected(self):
        admin_token = self._setup_admin()
        with self._app.get_db().sessionmaker() as session:
            admin_id = (
                session.scalars(select(User).where(User.username == "admin")).first().id
            )

        resp = self.fetch(
            f"/api/v2/users?id={admin_id}",
            method="PATCH",
            body=escape.json_encode({"is_admin": False}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(400, resp.code)
        self.assertEqual(
            "Cannot edit your own account", escape.json_decode(resp.body)["message"]
        )

    # note: the last-admin demotion guard (400 when target is the only admin) can only be
    # triggered by a concurrent race condition — current_user["is_admin"] is always re-fetched
    # from the DB on every request, so a synchronous test cannot reach that branch.

    # ─── DELETE /api/v2/users?id={n} ──────────────────────────────────────────

    def test_delete_user_success(self):
        admin_token = self._setup_admin()
        user_id = self._create_user(admin_token)

        resp = self.fetch(
            f"/api/v2/users?id={user_id}",
            method="DELETE",
            allow_nonstandard_methods=True,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(200, resp.code)
        self.assertEqual(
            "Successfully deleted user", escape.json_decode(resp.body)["message"]
        )

        with self._app.get_db().sessionmaker() as session:
            self.assertIsNone(session.get(User, user_id))

    def test_delete_requires_admin(self):
        admin_token = self._setup_admin()
        user_id = self._create_user(admin_token)
        resp = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "user", "password": "userpass"}),
        )
        user_token = escape.json_decode(resp.body)["access_token"]

        resp = self.fetch(
            f"/api/v2/users?id={user_id}",
            method="DELETE",
            allow_nonstandard_methods=True,
            headers={"Authorization": f"Bearer {user_token}"},
        )
        self.assertEqual(403, resp.code)

    def test_delete_missing_id(self):
        admin_token = self._setup_admin()
        resp = self.fetch(
            "/api/v2/users",
            method="DELETE",
            allow_nonstandard_methods=True,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(400, resp.code)
        self.assertEqual("Id missing", escape.json_decode(resp.body)["message"])

    def test_delete_user_not_found(self):
        admin_token = self._setup_admin()
        resp = self.fetch(
            "/api/v2/users?id=99999",
            method="DELETE",
            allow_nonstandard_methods=True,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(404, resp.code)
        self.assertEqual("User not found", escape.json_decode(resp.body)["message"])

    def test_delete_self_rejected(self):
        admin_token = self._setup_admin()
        with self._app.get_db().sessionmaker() as session:
            admin_id = (
                session.scalars(select(User).where(User.username == "admin")).first().id
            )

        resp = self.fetch(
            f"/api/v2/users?id={admin_id}",
            method="DELETE",
            allow_nonstandard_methods=True,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.assertEqual(400, resp.code)
        self.assertEqual(
            "Cannot delete currently authenticated user",
            escape.json_decode(resp.body)["message"],
        )

    # note: the last-admin delete guard (400 when target is the only admin) suffers the same
    # race-condition constraint as the PATCH guard — not reachable in a synchronous test.


class TestUsersV2JsonBodyValidation(DigiScriptTestCase):
    def test_create_user_invalid_json_returns_400(self):
        resp = self.fetch(
            "/api/v2/users", method="POST", body="nope", raise_error=False
        )
        self.assertEqual(400, resp.code)


class TestUsersV2Audit(DigiScriptTestCase):
    PASSWORD = "Sup3r-Secret-Pw-1"

    def _count(self, event, result):
        return (
            REGISTRY.get_sample_value(
                "digiscript_auth_events_total", {"event": event, "result": result}
            )
            or 0.0
        )

    def _req(self, path, method, body=None, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.fetch(
            path,
            method=method,
            body=None if method == "DELETE" else escape.json_encode(body or {}),
            headers=headers,
        )

    def _admin_token(self):
        resp = self._req(
            "/api/v2/users",
            "POST",
            {"username": "root", "password": self.PASSWORD, "is_admin": True},
        )
        self.assertEqual(200, resp.code)
        resp = self._req(
            "/api/v1/auth/login",
            "POST",
            {"username": "root", "password": self.PASSWORD},
        )
        return escape.json_decode(resp.body)["access_token"]

    def _no_secrets(self, logs, *secrets):
        output = "\n".join(logs.output)
        for secret in secrets:
            self.assertNotIn(secret, output)

    def test_create_update_delete_are_audited(self):
        # First-user bootstrap is unauthenticated: audited without an actor.
        with self.assertLogs("DigiScript", "INFO") as boot:
            token = self._admin_token()
        self.assertTrue(any("AUDIT user_create success" in o for o in boot.output))

        create_before = self._count("user_create", "success")
        update_before = self._count("user_update", "success")
        delete_before = self._count("user_delete", "success")
        with self.assertLogs("DigiScript", "INFO") as logs:
            self.assertEqual(
                200,
                self._req(
                    "/api/v2/users",
                    "POST",
                    {"username": "dave", "password": self.PASSWORD},
                    token,
                ).code,
            )
            with self._app.get_db().sessionmaker() as session:
                dave_id = (
                    session.scalars(select(User).where(User.username == "dave"))
                    .one()
                    .id
                )
            self.assertEqual(
                200,
                self._req(
                    f"/api/v2/users?id={dave_id}", "PATCH", {"is_admin": True}, token
                ).code,
            )
            self.assertEqual(
                200,
                self._req(f"/api/v2/users?id={dave_id}", "DELETE", None, token).code,
            )
        audit = [r.getMessage() for r in logs.records if r.name == "DigiScript.Audit"]
        self.assertTrue(any("AUDIT user_create success" in m for m in audit))
        self.assertTrue(
            any(
                "AUDIT user_update success" in m
                and f"target_user_id={dave_id}" in m
                and "is_admin=True" in m
                and 'username="root"' in m
                for m in audit
            )
        )
        self.assertTrue(
            any(
                "AUDIT user_delete success" in m and f"target_user_id={dave_id}" in m
                for m in audit
            )
        )
        self._no_secrets(logs, self.PASSWORD, token)
        self.assertEqual(create_before + 1, self._count("user_create", "success"))
        self.assertEqual(update_before + 1, self._count("user_update", "success"))
        self.assertEqual(delete_before + 1, self._count("user_delete", "success"))

    def test_create_failures_are_audited(self):
        token = self._admin_token()
        before = self._count("user_create", "failure")
        with self.assertLogs("DigiScript.Audit", "WARNING") as logs:
            taken = self._req(
                "/api/v2/users",
                "POST",
                {"username": "root", "password": self.PASSWORD},
                token,
            )
            weak = self._req(
                "/api/v2/users", "POST", {"username": "eve", "password": "a"}, token
            )
        self.assertEqual(400, taken.code)
        self.assertEqual(400, weak.code)
        self.assertIn("reason=username_taken", logs.output[0])
        self.assertIn("reason=weak_password", logs.output[1])
        self.assertEqual(before + 2, self._count("user_create", "failure"))
