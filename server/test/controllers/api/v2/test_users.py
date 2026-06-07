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
            "/api/v2/auth/login",
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
            "/api/v2/auth/login",
            method="POST",
            body=escape.json_encode({"username": "nonadmin", "password": "userpass"}),
        )
        nonadmin_token = escape.json_decode(resp.body)["access_token"]

        resp = self.fetch(
            "/api/v2/users",
            method="GET",
            headers={"Authorization": f"Bearer {nonadmin_token}"},
        )
        self.assertEqual(401, resp.code)

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
            "/api/v2/auth/login",
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
        self.assertEqual(401, resp.code)

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
            "/api/v2/auth/login",
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
        self.assertEqual(401, resp.code)

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
