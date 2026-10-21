import hashlib

import bcrypt
from tornado import escape

from models.user import User
from test.conftest import DigiScriptTestCase
from test.helpers.auth_fixtures import craft_token, make_user


class TestApiTokenV1API(DigiScriptTestCase):
    def _auth(self, user_id: int) -> dict:
        return {"Authorization": f"Bearer {craft_token(self._app, user_id)}"}

    def _post(self, path: str, user_id: int):
        return self.fetch(
            path,
            method="POST",
            body=escape.json_encode({}),
            headers=self._auth(user_id),
        )

    def _whoami(self, key: str):
        return self.fetch("/api/v1/auth", headers={"X-API-Key": key})

    def test_generated_key_is_stored_as_sha256_and_authenticates(self):
        user_id = make_user(self._app)
        response = self._post("/api/v1/auth/api-token/generate", user_id)
        self.assertEqual(200, response.code)
        key = escape.json_decode(response.body)["api_token"]
        with self._app.get_db().sessionmaker() as session:
            stored = session.get(User, user_id).api_token
        self.assertEqual(hashlib.sha256(key.encode()).hexdigest(), stored)
        self.assertEqual(200, self._whoami(key).code)

    def test_revoked_key_stops_authenticating(self):
        user_id = make_user(self._app)
        key = escape.json_decode(
            self._post("/api/v1/auth/api-token/generate", user_id).body
        )["api_token"]
        self.assertEqual(200, self._post("/api/v1/auth/api-token/revoke", user_id).code)
        self.assertEqual(401, self._whoami(key).code)

    def test_regenerating_replaces_a_legacy_key(self):
        user_id = make_user(self._app)
        with self._app.get_db().sessionmaker() as session:
            session.get(User, user_id).api_token = bcrypt.hashpw(
                b"old-legacy-key", bcrypt.gensalt(4)
            ).decode()
            session.commit()
        response = self._post("/api/v1/auth/api-token/generate", user_id)
        key = escape.json_decode(response.body)["api_token"]
        self.assertEqual(200, self._whoami(key).code)
        self.assertEqual(401, self._whoami("old-legacy-key").code)
