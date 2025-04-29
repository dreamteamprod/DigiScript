from tornado import escape

from .test_utils import DigiScriptTestCase


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
