from tornado import escape
from sqlalchemy import select

from models.user import User
from test.utils import DigiScriptTestCase


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

    def test_create_user_duplicate_username(self):
        """Test POST /api/v1/auth/create with duplicate username.

        This specifically tests the query at lines 48-49 in controllers/api/auth.py:
        session.scalars(select(User).where(User.username == username)).first()

        When a user with the same username already exists, the query should return
        that user and the endpoint should return a 400 error.
        """
        # Create an existing user directly in the database
        with self._app.get_db().sessionmaker() as session:
            existing_user = User(username="duplicate_test", password="hashed_pw")
            session.add(existing_user)
            session.commit()

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
        api_token = response_body["api_token"]

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

        # Create a test show (required by @requires_show decorator)
        with self._app.get_db().sessionmaker() as session:
            from models.show import Show

            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            show_id = show.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show_id)

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
        )

        # Get the user ID
        with self._app.get_db().sessionmaker() as session:
            from models.user import User

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
            from models.user import User

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

        # Create a test show (required by @requires_show decorator)
        with self._app.get_db().sessionmaker() as session:
            from models.show import Show

            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            show_id = show.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show_id)

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
        )
        self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {"username": "user2", "password": "password", "is_admin": False}
            ),
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
