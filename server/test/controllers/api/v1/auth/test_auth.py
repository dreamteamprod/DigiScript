from prometheus_client import REGISTRY
from sqlalchemy import select
from tornado import escape

from models.user import User
from test.conftest import DigiScriptTestCase
from test.helpers.auth_fixtures import craft_token, make_user


class TestAuthAPI(DigiScriptTestCase):
    def test_get(self):
        response = self.fetch("/api/v1/auth/create")
        self.assertEqual(405, response.code)

    def test_empty_post(self):
        response = self.fetch(
            "/api/v1/auth/create", method="POST", body=escape.json_encode({})
        )
        response_body = escape.json_decode(response.body)

        self.assertEqual(400, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("Username missing", response_body["message"])

    def test_missing_password(self):
        response = self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode({"username": "foobar"}),
        )
        response_body = escape.json_decode(response.body)

        self.assertEqual(400, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("Password missing", response_body["message"])

    def test_create_admin(self):
        response = self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "foobar",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )
        response_body = escape.json_decode(response.body)

        self.assertEqual(200, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("Successfully created user", response_body["message"])

    def test_create_first_user_must_be_admin(self):
        """Test that the first user created in the system must be an admin."""
        response = self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "firstuser", "password": "password", "is_admin": False}
            ),
        )
        response_body = escape.json_decode(response.body)

        self.assertEqual(400, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("First user must be an admin", response_body["message"])

    def test_create_user_duplicate_username(self):
        """Test POST /api/v1/auth/create with duplicate username.

        This specifically tests the query at lines 48-49 in controllers/api/auth.py:
        session.scalars(select(User).where(User.username == username)).first()

        When a user with the same username already exists, the query should return
        that user and the endpoint should return a 400 error.
        """
        # Create initial admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "duplicate_test",
                    "password": "adminpass",
                    "is_admin": True,
                }
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode(
                {"username": "duplicate_test", "password": "adminpass"}
            ),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Try to create a user with the same username
        response = self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "duplicate_test",
                    "password": "password123",
                    "is_admin": False,
                }
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        response_body = escape.json_decode(response.body)

        self.assertEqual(400, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("Username already taken", response_body["message"])

    def test_login_success(self):
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "foobar",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "foobar", "password": "password"}),
        )
        response_body = escape.json_decode(response.body)
        self.assertEqual(200, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("Successful log in", response_body["message"])

    def test_login_invalid_password(self):
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "foobar",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode(
                {"username": "foobar", "password": "wrongpassword"}
            ),
        )
        response_body = escape.json_decode(response.body)
        self.assertEqual(401, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("Invalid username/password", response_body["message"])

    def test_login_invalid_username(self):
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "foobar",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode(
                {"username": "wrongusername", "password": "password"}
            ),
        )
        response_body = escape.json_decode(response.body)
        self.assertEqual(401, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("Invalid username/password", response_body["message"])

    def test_jwt_logout_revoke(self):
        # Create a test user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "foobar",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )

        # Log in to that test user
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "foobar", "password": "password"}),
        )

        response_body = escape.json_decode(response.body)
        self.assertEqual(200, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("Successful log in", response_body["message"])

        token = response_body["access_token"]

        # Log out of the test user
        response = self.fetch(
            "/api/v1/auth/logout",
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {token}"},
        )
        response_body = escape.json_decode(response.body)
        self.assertEqual(200, response.code)
        self.assertTrue("message" in response_body)
        self.assertEqual("Successfully logged out", response_body["message"])

        # Try to use this token to do something else, should get 401 back
        response = self.fetch(
            "/api/v1/auth", method="GET", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(401, response.code)

    def test_api_token_generate(self):
        # Create and login a user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "foobar",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "foobar", "password": "password"}),
        )
        response_body = escape.json_decode(response.body)
        token = response_body["access_token"]

        # Generate API token
        response = self.fetch(
            "/api/v1/auth/api-token/generate",
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {token}"},
        )
        response_body = escape.json_decode(response.body)
        self.assertEqual(200, response.code)
        self.assertTrue("api_token" in response_body)
        self.assertTrue(len(response_body["api_token"]) > 0)

    def test_api_token_authentication(self):
        # Create and login a user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "foobar",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "foobar", "password": "password"}),
        )
        response_body = escape.json_decode(response.body)
        token = response_body["access_token"]

        # Generate API token
        response = self.fetch(
            "/api/v1/auth/api-token/generate",
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {token}"},
        )
        response_body = escape.json_decode(response.body)
        api_token = response_body["api_token"]

        # Use API token to authenticate
        response = self.fetch(
            "/api/v1/auth", method="GET", headers={"X-API-Key": api_token}
        )
        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertEqual("foobar", response_body["username"])

    def test_api_token_invalid(self):
        # Try to use an invalid API token
        response = self.fetch(
            "/api/v1/auth", method="GET", headers={"X-API-Key": "invalid-token"}
        )
        self.assertEqual(401, response.code)

    def test_api_token_revoke(self):
        # Create and login a user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "foobar",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "foobar", "password": "password"}),
        )
        response_body = escape.json_decode(response.body)
        token = response_body["access_token"]

        # Generate API token
        response = self.fetch(
            "/api/v1/auth/api-token/generate",
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {token}"},
        )
        response_body = escape.json_decode(response.body)
        api_token = response_body["api_token"]

        # Verify API token works
        response = self.fetch(
            "/api/v1/auth", method="GET", headers={"X-API-Key": api_token}
        )
        self.assertEqual(200, response.code)

        # Revoke API token
        response = self.fetch(
            "/api/v1/auth/api-token/revoke",
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, response.code)

        # Verify API token no longer works
        response = self.fetch(
            "/api/v1/auth", method="GET", headers={"X-API-Key": api_token}
        )
        self.assertEqual(401, response.code)

    def test_api_token_get(self):
        # Create and login a user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "foobar",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "foobar", "password": "password"}),
        )
        response_body = escape.json_decode(response.body)
        token = response_body["access_token"]

        # Check no token exists initially
        response = self.fetch(
            "/api/v1/auth/api-token",
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )
        response_body = escape.json_decode(response.body)
        self.assertEqual(200, response.code)
        self.assertFalse(response_body["has_token"])

        # Generate API token
        response = self.fetch(
            "/api/v1/auth/api-token/generate",
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {token}"},
        )
        response_body = escape.json_decode(response.body)

        # Check that token exists (but can't retrieve it)
        response = self.fetch(
            "/api/v1/auth/api-token",
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )
        response_body = escape.json_decode(response.body)
        self.assertEqual(200, response.code)
        self.assertTrue(response_body["has_token"])

    def test_delete_user(self):
        """Test DELETE /api/v1/auth/delete endpoint.

        This tests the queries at lines 116-118 and 129-131 in controllers/api/auth.py:
        session.scalars(select(Session).where(Session.user_id == user_to_delete.id)).all()

        When deleting a user, the endpoint queries for all active WebSocket sessions
        belonging to that user. In this test, there are no active sessions, so the
        query returns an empty list and deletion proceeds normally.
        """
        # Create admin user for authentication
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "password", "is_admin": True}
            ),
        )

        # Login as admin to get token
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "password"}),
        )
        response_body = escape.json_decode(response.body)
        admin_token = response_body["access_token"]

        # Create a non-admin user to delete
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "userToDelete", "password": "password", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Get the user ID
        with self._app.get_db().sessionmaker() as session:
            user = session.scalars(
                select(User).where(User.username == "userToDelete")
            ).first()
            user_id = user.id

        # Delete the user - the session query will return empty list
        response = self.fetch(
            "/api/v1/auth/delete",
            method="POST",
            body=escape.json_encode({"id": user_id}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Verify deletion was successful
        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertEqual("Successfully deleted user", response_body["message"])

        # Verify user was deleted
        with self._app.get_db().sessionmaker() as session:
            deleted_user = session.scalars(
                select(User).where(User.id == user_id)
            ).first()
            self.assertIsNone(deleted_user)

    def test_get_users(self):
        """Test GET /api/v1/auth/users endpoint.

        This tests the query at line 266 in controllers/api/auth.py:
        session.scalars(select(User)).all()

        The endpoint retrieves all users in the system.
        """
        # Create admin user for authentication
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "password", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "password"}),
        )
        response_body = escape.json_decode(response.body)
        admin_token = response_body["access_token"]

        # Create additional users
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "user1", "password": "password", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "user2", "password": "password", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Get all users
        response = self.fetch(
            "/api/v1/auth/users",
            method="GET",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Verify response
        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("users", response_body)
        self.assertEqual(3, len(response_body["users"]))  # admin, user1, user2

        # Verify usernames are in response
        usernames = [u["username"] for u in response_body["users"]]
        self.assertIn("admin", usernames)
        self.assertIn("user1", usernames)
        self.assertIn("user2", usernames)

    def test_change_password_success(self):
        """Test successful password change with valid old password"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create and login a user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "testuser", "password": "oldpass123", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "testuser", "password": "oldpass123"}),
        )
        token = escape.json_decode(response.body)["access_token"]

        # Change password
        response = self.fetch(
            "/api/v1/auth/change-password",
            method="PATCH",
            body=escape.json_encode(
                {"old_password": "oldpass123", "new_password": "newpass456"}
            ),
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertEqual("Password changed successfully", response_body["message"])
        self.assertIn("access_token", response_body)
        self.assertIn("token_type", response_body)

        new_token = response_body["access_token"]

        # Verify old token is invalidated (should get 401)
        response = self.fetch(
            "/api/v1/auth", method="GET", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(401, response.code)

        # Verify new token works (user stays logged in)
        response = self.fetch(
            "/api/v1/auth",
            method="GET",
            headers={"Authorization": f"Bearer {new_token}"},
        )
        self.assertEqual(200, response.code)

        # Verify can login with new password
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "testuser", "password": "newpass456"}),
        )
        self.assertEqual(200, response.code)

    def test_change_password_incorrect_old_password(self):
        """Test password change fails with incorrect old password"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create and login a user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "testuser", "password": "oldpass123", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "testuser", "password": "oldpass123"}),
        )
        token = escape.json_decode(response.body)["access_token"]

        # Try to change password with wrong old password
        response = self.fetch(
            "/api/v1/auth/change-password",
            method="PATCH",
            body=escape.json_encode(
                {"old_password": "wrongpass", "new_password": "newpass456"}
            ),
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(401, response.code)
        response_body = escape.json_decode(response.body)
        self.assertEqual("Current password is incorrect", response_body["message"])

    def test_change_password_missing_new_password(self):
        """Test password change fails when new password is missing"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create and login a user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "testuser", "password": "oldpass123", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "testuser", "password": "oldpass123"}),
        )
        token = escape.json_decode(response.body)["access_token"]

        # Try to change password without new password
        response = self.fetch(
            "/api/v1/auth/change-password",
            method="PATCH",
            body=escape.json_encode({"old_password": "oldpass123"}),
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertEqual("New password is required", response_body["message"])

    def test_change_password_weak_password(self):
        """Test password change fails with weak new password"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create and login a user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "testuser", "password": "oldpass123", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "testuser", "password": "oldpass123"}),
        )
        token = escape.json_decode(response.body)["access_token"]

        # Try to change to weak password (< 6 characters)
        response = self.fetch(
            "/api/v1/auth/change-password",
            method="PATCH",
            body=escape.json_encode(
                {"old_password": "oldpass123", "new_password": "123"}
            ),
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("at least 6 characters", response_body["message"])

    def test_change_password_requires_authentication(self):
        """Test password change requires authentication"""
        response = self.fetch(
            "/api/v1/auth/change-password",
            method="PATCH",
            body=escape.json_encode(
                {"old_password": "oldpass", "new_password": "newpass"}
            ),
        )

        self.assertEqual(401, response.code)

    def test_change_password_with_requires_password_change_flag(self):
        """Test password change works without old password when requires_password_change=True"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create user via API to ensure password is properly hashed
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "forcedchange",
                    "password": "temppass123",
                    "is_admin": False,
                }
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Set requires_password_change flag
        with self._app.get_db().sessionmaker() as session:
            user = session.scalars(
                select(User).where(User.username == "forcedchange")
            ).first()
            user.requires_password_change = True
            session.commit()
            user_id = user.id

        # Login
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode(
                {"username": "forcedchange", "password": "temppass123"}
            ),
        )
        token = escape.json_decode(response.body)["access_token"]

        # Change password without providing old password
        response = self.fetch(
            "/api/v1/auth/change-password",
            method="PATCH",
            body=escape.json_encode({"new_password": "newpass123"}),
            headers={"Authorization": f"Bearer {token}"},
        )

        self.assertEqual(200, response.code)

        # Verify requires_password_change is now False
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            self.assertFalse(user.requires_password_change)

    def test_password_enforcement_blocks_regular_endpoints(self):
        """Test that requires_password_change blocks access to regular endpoints"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create user with requires_password_change=True
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "forcechange",
                    "password": "password123",
                    "is_admin": False,
                }
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Log in to get JWT
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode(
                {"username": "forcechange", "password": "password123"}
            ),
        )
        self.assertEqual(200, response.code)
        token = escape.json_decode(response.body)["access_token"]

        # Set requires_password_change=True
        with self._app.get_db().sessionmaker() as session:
            user = session.scalars(
                select(User).where(User.username == "forcechange")
            ).first()
            user.requires_password_change = True
            session.commit()

        # Try to access a regular endpoint (should be blocked with 403)
        response = self.fetch(
            "/api/v1/auth/api-token",
            method="GET",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(403, response.code)

    def test_password_enforcement_allows_change_password_endpoint(self):
        """Test that requires_password_change allows access to change-password"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create user with requires_password_change=True
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "forcechange2",
                    "password": "password123",
                    "is_admin": False,
                }
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Log in to get JWT
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode(
                {"username": "forcechange2", "password": "password123"}
            ),
        )
        self.assertEqual(200, response.code)
        token = escape.json_decode(response.body)["access_token"]

        # Set requires_password_change=True
        with self._app.get_db().sessionmaker() as session:
            user = session.scalars(
                select(User).where(User.username == "forcechange2")
            ).first()
            user.requires_password_change = True
            session.commit()

        # Try to change password (should be allowed)
        response = self.fetch(
            "/api/v1/auth/change-password",
            method="PATCH",
            body=escape.json_encode({"new_password": "newpassword123"}),
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, response.code)

    def test_password_enforcement_allows_logout_endpoint(self):
        """Test that requires_password_change allows access to logout"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create user with requires_password_change=True
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "forcechange3",
                    "password": "password123",
                    "is_admin": False,
                }
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Log in to get JWT
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode(
                {"username": "forcechange3", "password": "password123"}
            ),
        )
        self.assertEqual(200, response.code)
        token = escape.json_decode(response.body)["access_token"]

        # Set requires_password_change=True
        with self._app.get_db().sessionmaker() as session:
            user = session.scalars(
                select(User).where(User.username == "forcechange3")
            ).first()
            user.requires_password_change = True
            session.commit()

        # Try to logout (should be allowed)
        response = self.fetch(
            "/api/v1/auth/logout",
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, response.code)

    def test_admin_reset_password_success(self):
        """Test admin can successfully reset another user's password"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create a regular user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "regularuser", "password": "userpass", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Get user ID
        with self._app.get_db().sessionmaker() as session:
            user = session.scalars(
                select(User).where(User.username == "regularuser")
            ).first()
            if not user:
                self.fail("User 'regularuser' not found in database")
            user_id = user.id

        # Admin resets user password
        response = self.fetch(
            "/api/v1/auth/reset-password",
            method="POST",
            body=escape.json_encode({"user_id": user_id}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertEqual("Password reset successfully", response_body["message"])
        self.assertIn("temporary_password", response_body)

        temp_password = response_body["temporary_password"]

        # Verify temporary password works
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode(
                {"username": "regularuser", "password": temp_password}
            ),
        )
        self.assertEqual(200, response.code)

        # Verify requires_password_change is True
        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, user_id)
            self.assertTrue(user.requires_password_change)

    def test_admin_reset_password_cannot_reset_own(self):
        """Test admin cannot reset their own password via admin endpoint"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Get admin user ID
        with self._app.get_db().sessionmaker() as session:
            admin = session.scalars(
                select(User).where(User.username == "admin")
            ).first()
            admin_id = admin.id

        # Try to reset own password
        response = self.fetch(
            "/api/v1/auth/reset-password",
            method="POST",
            body=escape.json_encode({"user_id": admin_id}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("Cannot reset your own password", response_body["message"])

    def test_admin_reset_password_requires_admin(self):
        """Test password reset requires admin privileges"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Create regular user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "regularuser", "password": "userpass", "is_admin": False}
            ),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        # Login as regular user
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode(
                {"username": "regularuser", "password": "userpass"}
            ),
        )
        user_token = escape.json_decode(response.body)["access_token"]

        # Try to reset password without admin privileges
        response = self.fetch(
            "/api/v1/auth/reset-password",
            method="POST",
            body=escape.json_encode({"user_id": 999}),
            headers={"Authorization": f"Bearer {user_token}"},
        )

        self.assertEqual(403, response.code)

    def test_admin_reset_password_user_not_found(self):
        """Test password reset fails for non-existent user"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Try to reset password for non-existent user
        response = self.fetch(
            "/api/v1/auth/reset-password",
            method="POST",
            body=escape.json_encode({"user_id": 99999}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(404, response.code)
        response_body = escape.json_decode(response.body)
        self.assertEqual("User not found", response_body["message"])

    def test_admin_reset_password_missing_user_id(self):
        """Test password reset fails when user_id is missing"""
        # Create admin user
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "admin", "password": "adminpass", "is_admin": True}
            ),
        )

        # Login as admin
        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "adminpass"}),
        )
        admin_token = escape.json_decode(response.body)["access_token"]

        # Try to reset password without user_id
        response = self.fetch(
            "/api/v1/auth/reset-password",
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertEqual("user_id is required", response_body["message"])


class TestAuthTokenLifecycleAPI(DigiScriptTestCase):
    def _post(self, path: str, token: str):
        return self.fetch(
            path,
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {token}"},
        )

    def test_logged_out_token_is_rejected(self):
        token = craft_token(self._app, make_user(self._app))
        self.assertEqual(200, self._post("/api/v1/auth/logout", token).code)
        response = self.fetch(
            "/api/v1/auth", headers={"Authorization": f"Bearer {token}"}
        )
        self.assertEqual(401, response.code)


class TestAuthJsonBodyValidation(DigiScriptTestCase):
    def _post(self, path, body, token=None, method="POST"):
        return self.fetch(
            path,
            method=method,
            body=body,
            headers={"Authorization": f"Bearer {token}"} if token else {},
            raise_error=False,
        )

    def test_login_invalid_json_returns_400(self):
        self.assertEqual(400, self._post("/api/v1/auth/login", "{not json").code)

    def test_login_non_object_json_returns_400(self):
        self.assertEqual(400, self._post("/api/v1/auth/login", "[1, 2]").code)

    def test_login_bare_json_string_returns_400(self):
        self.assertEqual(400, self._post("/api/v1/auth/login", '"secret"').code)

    def test_login_empty_body_returns_400(self):
        self.assertEqual(400, self._post("/api/v1/auth/login", "").code)

    def test_create_user_invalid_json_returns_400(self):
        self.assertEqual(400, self._post("/api/v1/auth/create", "nope").code)

    def test_change_password_invalid_json_returns_400(self):
        token = self._create_and_login_admin()
        resp = self._post("/api/v1/auth/change-password", "nope", token, "PATCH")
        self.assertEqual(400, resp.code)


class TestAuthAuditLogging(DigiScriptTestCase):
    """Auth endpoints emit ``DigiScript.Audit`` lines and bump the counter."""

    PASSWORD = "Sup3r-Secret-Pw-1"
    NEW_PASSWORD = "N3w-Secret-Pw-2"

    def _count(self, event: str, result: str) -> float:
        return (
            REGISTRY.get_sample_value(
                "digiscript_auth_events_total", {"event": event, "result": result}
            )
            or 0.0
        )

    def _post(self, path, body=None, token=None, method="POST"):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.fetch(
            path,
            method=method,
            body=escape.json_encode(body or {}),
            headers=headers,
        )

    def _create(self, username="alice", is_admin=True):
        response = self._post(
            "/api/v1/auth/create",
            {"username": username, "password": self.PASSWORD, "is_admin": is_admin},
        )
        self.assertEqual(200, response.code)

    def _login(self, username="alice", password=None):
        return self._post(
            "/api/v1/auth/login",
            {"username": username, "password": password or self.PASSWORD},
        )

    def _token(self, username="alice"):
        return escape.json_decode(self._login(username).body)["access_token"]

    def _assert_no_secrets(self, logs, *secrets):
        output = "\n".join(logs.output)
        for secret in secrets:
            self.assertNotIn(secret, output)

    def test_login_success(self):
        self._create()
        before = self._count("login", "success")
        with self.assertLogs("DigiScript", "INFO") as logs:
            response = self._login()
        self.assertEqual(200, response.code)
        token = escape.json_decode(response.body)["access_token"]
        audit = [r for r in logs.records if r.name == "DigiScript.Audit"]
        self.assertEqual(1, len(audit))
        self.assertEqual("INFO", audit[0].levelname)
        self.assertIn("AUDIT login success", audit[0].getMessage())
        self.assertIn('username="alice"', audit[0].getMessage())
        self.assertEqual("alice", audit[0].username)
        self.assertIsNotNone(audit[0].user_id)
        self.assertTrue(audit[0].remote_ip)
        self._assert_no_secrets(logs, self.PASSWORD, token)
        self.assertEqual(before + 1, self._count("login", "success"))

    def test_login_failure_reasons_differ_in_log_but_not_response(self):
        self._create()
        before = self._count("login", "failure")
        with self.assertLogs("DigiScript.Audit", "WARNING") as bad_pw:
            bad_password = self._login(password="wrong-Secret-Pw-9")
        with self.assertLogs("DigiScript.Audit", "WARNING") as unknown:
            unknown_user = self._login(username="mallory")
        self.assertEqual(401, bad_password.code)
        self.assertEqual(bad_password.code, unknown_user.code)
        self.assertEqual(bad_password.body, unknown_user.body)
        self.assertIn("reason=bad_password", bad_pw.output[0])
        self.assertIn("reason=unknown_user", unknown.output[0])
        self.assertEqual("WARNING", bad_pw.records[0].levelname)
        self._assert_no_secrets(bad_pw, "wrong-Secret-Pw-9", self.PASSWORD)
        self.assertEqual(before + 2, self._count("login", "failure"))

    def test_login_failure_sanitises_username(self):
        hostile = 'bob" ip=6.6.6.6\r\nAUDIT login success\x1b[31m' + "x" * 200
        with self.assertLogs("DigiScript.Audit", "WARNING") as logs:
            response = self._login(username=hostile)
        self.assertEqual(401, response.code)
        self.assertEqual(1, len(logs.output))
        message = logs.records[0].getMessage()
        self.assertNotIn("\n", message)
        self.assertNotIn("\r", message)
        self.assertNotIn("\x1b", message)
        self.assertLessEqual(len(logs.records[0].username), 64)
        self.assertTrue(message.startswith("AUDIT login failure username="))

    def test_logout(self):
        self._create()
        token = self._token()
        before = self._count("logout", "success")
        with self.assertLogs("DigiScript", "INFO") as logs:
            response = self._post("/api/v1/auth/logout", token=token)
        self.assertEqual(200, response.code)
        self.assertTrue(any("AUDIT logout success" in o for o in logs.output))
        self._assert_no_secrets(logs, token)
        self.assertEqual(before + 1, self._count("logout", "success"))

    def test_refresh_token(self):
        self._create()
        token = self._token()
        before = self._count("token_refresh", "success")
        with self.assertLogs("DigiScript", "INFO") as logs:
            response = self._post("/api/v1/auth/refresh-token", token=token)
        self.assertEqual(200, response.code)
        new_token = escape.json_decode(response.body)["access_token"]
        self.assertTrue(any("AUDIT token_refresh success" in o for o in logs.output))
        self._assert_no_secrets(logs, token, new_token)
        self.assertEqual(before + 1, self._count("token_refresh", "success"))

    def test_change_password_success_and_failure(self):
        self._create()
        token = self._token()
        ok_before = self._count("password_change", "success")
        fail_before = self._count("password_change", "failure")

        with self.assertLogs("DigiScript", "INFO") as logs:
            bad = self._post(
                "/api/v1/auth/change-password",
                {"old_password": "wrong-Secret-Pw-9", "new_password": "x-Pw-3"},
                token=token,
                method="PATCH",
            )
        self.assertEqual(401, bad.code)
        self.assertTrue(any("reason=bad_old_password" in o for o in logs.output))
        self._assert_no_secrets(logs, "wrong-Secret-Pw-9", self.PASSWORD, "x-Pw-3")

        with self.assertLogs("DigiScript", "INFO") as logs:
            good = self._post(
                "/api/v1/auth/change-password",
                {"old_password": self.PASSWORD, "new_password": self.NEW_PASSWORD},
                token=token,
                method="PATCH",
            )
        self.assertEqual(200, good.code)
        new_token = escape.json_decode(good.body)["access_token"]
        self.assertTrue(any("AUDIT password_change success" in o for o in logs.output))
        self._assert_no_secrets(logs, self.PASSWORD, self.NEW_PASSWORD, new_token)
        self.assertEqual(ok_before + 1, self._count("password_change", "success"))
        self.assertEqual(fail_before + 1, self._count("password_change", "failure"))

    def test_change_password_weak_new_password_is_audited(self):
        self._create()
        token = self._token()
        with self.assertLogs("DigiScript.Audit", "WARNING") as logs:
            response = self._post(
                "/api/v1/auth/change-password",
                {"old_password": self.PASSWORD, "new_password": "a"},
                token=token,
                method="PATCH",
            )
        self.assertEqual(400, response.code)
        self.assertIn("reason=invalid_new_password", logs.output[0])

    def test_admin_reset_password(self):
        self._create()
        token = self._token()
        bob_id = make_user(self._app, username="bob", is_admin=False)
        before = self._count("password_reset", "success")
        with self.assertLogs("DigiScript", "INFO") as logs:
            response = self._post(
                "/api/v1/auth/reset-password", {"user_id": bob_id}, token=token
            )
        self.assertEqual(200, response.code)
        temp = escape.json_decode(response.body)["temporary_password"]
        audit = [r for r in logs.records if r.name == "DigiScript.Audit"]
        self.assertEqual(1, len(audit))
        self.assertIn("AUDIT password_reset success", audit[0].getMessage())
        self.assertIn(f"target_user_id={bob_id}", audit[0].getMessage())
        self.assertEqual("alice", audit[0].username)
        self._assert_no_secrets(logs, temp, self.PASSWORD)
        self.assertEqual(before + 1, self._count("password_reset", "success"))


class TestAuthUserAdminAudit(DigiScriptTestCase):
    PASSWORD = "Sup3r-Secret-Pw-1"

    def _count(self, event, result):
        return (
            REGISTRY.get_sample_value(
                "digiscript_auth_events_total", {"event": event, "result": result}
            )
            or 0.0
        )

    def _post(self, path, body, token=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        return self.fetch(
            path, method="POST", body=escape.json_encode(body), headers=headers
        )

    def test_user_create_and_delete_are_audited(self):
        with self.assertLogs("DigiScript.Audit", "INFO") as boot:
            self._post(
                "/api/v1/auth/create",
                {"username": "root", "password": self.PASSWORD, "is_admin": True},
            )
        self.assertIn("AUDIT user_create success", boot.output[0])
        token = escape.json_decode(
            self._post(
                "/api/v1/auth/login", {"username": "root", "password": self.PASSWORD}
            ).body
        )["access_token"]

        create_before = self._count("user_create", "success")
        fail_before = self._count("user_create", "failure")
        delete_before = self._count("user_delete", "success")
        with self.assertLogs("DigiScript", "INFO") as logs:
            self.assertEqual(
                200,
                self._post(
                    "/api/v1/auth/create",
                    {"username": "dave", "password": self.PASSWORD},
                    token,
                ).code,
            )
            self.assertEqual(
                400,
                self._post(
                    "/api/v1/auth/create",
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
                200, self._post("/api/v1/auth/delete", {"id": dave_id}, token).code
            )
        output = "\n".join(logs.output)
        self.assertIn("AUDIT user_create success", output)
        self.assertIn("reason=username_taken", output)
        self.assertIn("AUDIT user_delete success", output)
        self.assertIn(f"target_user_id={dave_id}", output)
        self.assertNotIn(self.PASSWORD, output)
        self.assertNotIn(token, output)
        self.assertEqual(create_before + 1, self._count("user_create", "success"))
        self.assertEqual(fail_before + 1, self._count("user_create", "failure"))
        self.assertEqual(delete_before + 1, self._count("user_delete", "success"))
