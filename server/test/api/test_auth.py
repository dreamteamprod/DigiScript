from tornado import escape

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
        session.query(User).filter(User.username == username).first()

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
