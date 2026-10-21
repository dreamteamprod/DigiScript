import hashlib

from tornado import escape

from models.user import User
from test.conftest import DigiScriptTestCase
from test.helpers.auth_fixtures import craft_token, make_user


class TestUsersTokenV2API(DigiScriptTestCase):
    def _headers(self, user_id: int) -> dict:
        return {"Authorization": f"Bearer {craft_token(self._app, user_id)}"}

    def _whoami(self, key: str):
        return self.fetch("/api/v1/auth", headers={"X-API-Key": key})

    def test_generated_key_is_stored_as_sha256_and_authenticates(self):
        user_id = make_user(self._app)
        response = self.fetch(
            "/api/v2/users/token",
            method="POST",
            body=escape.json_encode({}),
            headers=self._headers(user_id),
        )
        self.assertEqual(200, response.code)
        key = escape.json_decode(response.body)["api_token"]
        with self._app.get_db().sessionmaker() as session:
            stored = session.get(User, user_id).api_token
        self.assertEqual(hashlib.sha256(key.encode()).hexdigest(), stored)
        self.assertEqual(200, self._whoami(key).code)

    def test_has_token_reflects_state_and_delete_revokes_key(self):
        user_id = make_user(self._app)
        headers = self._headers(user_id)
        has = lambda: escape.json_decode(  # noqa: E731
            self.fetch("/api/v2/users/token", headers=headers).body
        )["has_token"]
        self.assertFalse(has())
        key = escape.json_decode(
            self.fetch(
                "/api/v2/users/token",
                method="POST",
                body=escape.json_encode({}),
                headers=headers,
            ).body
        )["api_token"]
        self.assertTrue(has())
        response = self.fetch("/api/v2/users/token", method="DELETE", headers=headers)
        self.assertEqual(200, response.code)
        self.assertFalse(has())
        self.assertEqual(401, self._whoami(key).code)
