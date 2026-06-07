from sqlalchemy import select
from tornado import escape

from models.user import User
from test.conftest import DigiScriptTestCase


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

        self.assertEqual(401, response.code)

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
