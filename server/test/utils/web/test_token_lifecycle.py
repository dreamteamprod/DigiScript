import hashlib
import importlib.util
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from unittest import TestCase

import bcrypt
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from jwt import PyJWT
from sqlalchemy import select
from tornado import escape
from tornado.httpclient import HTTPRequest
from tornado.testing import gen_test
from tornado.websocket import websocket_connect

from models.user import RevokedToken, User
from test.conftest import DigiScriptTestCase
from utils.web.jwt_service import JWTService


class _LifecycleBase(DigiScriptTestCase):
    def _make_user(self, username="admin", is_admin=True) -> int:
        with self._app.get_db().sessionmaker() as session:
            user = User(username=username, password="hashed", is_admin=is_admin)
            session.add(user)
            session.commit()
            return user.id

    def _craft(self, user_id: int, **overrides) -> str:
        now = datetime.now(tz=timezone.utc)
        with self._app.get_db().sessionmaker() as session:
            version = session.get(User, user_id).token_version
        payload = {
            "user_id": user_id,
            "token_version": version,
            "iat": now,
            "auth_time": int(now.timestamp()),
            "exp": now + timedelta(hours=1),
            "jti": "crafted-jti",
        }
        payload.update(overrides)
        return PyJWT().encode(payload, self._app.jwt_service.get_secret())

    async def _ws_auth_reply(self, token: str) -> dict:
        ws = await websocket_connect(
            self.get_url("/api/v1/ws").replace("http://", "ws://")
        )
        await ws.read_message()  # internal uuid
        await ws.read_message()  # GET_SETTINGS
        await ws.write_message(
            json.dumps({"OP": "AUTHENTICATE", "DATA": {"token": token}})
        )
        reply = json.loads(await ws.read_message())
        ws.close()
        return reply


class TestSharedValidation(_LifecycleBase):
    def _bump_version(self, user_id: int):
        with self._app.get_db().sessionmaker() as session:
            session.get(User, user_id).token_version += 1
            session.commit()

    @gen_test
    async def test_ws_rejects_stale_token_version(self):
        user_id = self._make_user()
        token = self._craft(user_id)
        self.assertEqual("WS_AUTH_SUCCESS", (await self._ws_auth_reply(token))["OP"])
        self._bump_version(user_id)
        reply = await self._ws_auth_reply(token)
        self.assertEqual("WS_AUTH_ERROR", reply["OP"])

    @gen_test
    async def test_rest_rejects_stale_token_version(self):
        user_id = self._make_user()
        token = self._craft(user_id)
        self._bump_version(user_id)
        response = await self.http_client.fetch(
            HTTPRequest(
                self.get_url("/api/v1/auth"),
                headers={"Authorization": f"Bearer {token}"},
            ),
            raise_error=False,
        )
        self.assertEqual(401, response.code)

    @gen_test
    async def test_ws_rejects_revoked_token(self):
        user_id = self._make_user()
        token = self._craft(user_id)
        await self._app.jwt_service.revoke_token(token)
        self.assertEqual("WS_AUTH_ERROR", (await self._ws_auth_reply(token))["OP"])


class TestRevocationPersistence(_LifecycleBase):
    @gen_test
    async def test_revocation_survives_service_restart(self):
        user_id = self._make_user()
        token = self._craft(user_id)
        await self._app.jwt_service.revoke_token(token)

        fresh_service = JWTService(application=self._app)
        self.assertTrue(await fresh_service.is_token_revoked(token))
        other = self._craft(user_id, jti="another-jti")
        self.assertFalse(await fresh_service.is_token_revoked(other))

    @gen_test
    async def test_expired_revocations_are_pruned(self):
        user_id = self._make_user()
        now = int(datetime.now(tz=timezone.utc).timestamp())
        with self._app.get_db().sessionmaker() as session:
            session.add(RevokedToken(jti="stale", expires_at=now - 10))
            session.commit()

        await self._app.jwt_service.revoke_token(self._craft(user_id, jti="live"))

        with self._app.get_db().sessionmaker() as session:
            jtis = set(session.scalars(select(RevokedToken.jti)).all())
        self.assertEqual({"live"}, jtis)

    @gen_test
    async def test_logout_revokes_by_jti(self):
        user_id = self._make_user()
        token = self._craft(user_id)
        response = await self.http_client.fetch(
            HTTPRequest(
                self.get_url("/api/v1/auth/logout"),
                method="POST",
                body=escape.json_encode({}),
                headers={"Authorization": f"Bearer {token}"},
            ),
            raise_error=False,
        )
        self.assertEqual(200, response.code)
        response = await self.http_client.fetch(
            HTTPRequest(
                self.get_url("/api/v1/auth"),
                headers={"Authorization": f"Bearer {token}"},
            ),
            raise_error=False,
        )
        self.assertEqual(401, response.code)


class TestSessionCap(_LifecycleBase):
    def _old_session_token(self) -> str:
        user_id = self._make_user()
        started = datetime.now(tz=timezone.utc) - timedelta(days=31)
        return self._craft(user_id, auth_time=int(started.timestamp()))

    @gen_test
    async def test_rest_rejects_session_past_cap(self):
        token = self._old_session_token()
        response = await self.http_client.fetch(
            HTTPRequest(
                self.get_url("/api/v1/auth"),
                headers={"Authorization": f"Bearer {token}"},
            ),
            raise_error=False,
        )
        self.assertEqual(401, response.code)

    @gen_test
    async def test_ws_rejects_session_past_cap(self):
        reply = await self._ws_auth_reply(self._old_session_token())
        self.assertEqual("WS_AUTH_ERROR", reply["OP"])

    @gen_test
    async def test_refresh_carries_auth_time_forward(self):
        user_id = self._make_user()
        started = int((datetime.now(tz=timezone.utc) - timedelta(days=3)).timestamp())
        token = self._craft(user_id, auth_time=started)
        response = await self.http_client.fetch(
            HTTPRequest(
                self.get_url("/api/v1/auth/refresh-token"),
                method="POST",
                body=escape.json_encode({}),
                headers={"Authorization": f"Bearer {token}"},
            )
        )
        refreshed = self._app.jwt_service.decode_access_token(
            escape.json_decode(response.body)["access_token"]
        )
        self.assertEqual(started, refreshed["auth_time"])

    def test_new_login_sets_auth_time(self):
        token = self._app.jwt_service.create_access_token({"user_id": 1})
        payload = self._app.jwt_service.decode_access_token(token)
        self.assertIn("auth_time", payload)


class TestApiKeys(_LifecycleBase):
    def _generate(self, user_id: int, path="/api/v1/auth/api-token/generate") -> str:
        token = self._craft(user_id)
        response = self.fetch(
            path,
            method="POST",
            body=escape.json_encode({}),
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(200, response.code)
        return escape.json_decode(response.body)["api_token"]

    def _whoami(self, key: str):
        return self.fetch("/api/v1/auth", headers={"X-API-Key": key})

    def test_key_format_and_hashed_storage(self):
        user_id = self._make_user()
        key = self._generate(user_id)
        prefix, secret = key.split(".", 1)
        self.assertEqual(str(user_id), prefix)
        with self._app.get_db().sessionmaker() as session:
            stored = session.get(User, user_id).api_token
        self.assertEqual(hashlib.sha256(secret.encode()).hexdigest(), stored)
        self.assertEqual(200, self._whoami(key).code)

    def test_v2_generate_uses_new_format(self):
        user_id = self._make_user()
        key = self._generate(user_id, "/api/v2/users/token")
        self.assertTrue(key.startswith(f"{user_id}."))
        self.assertEqual(200, self._whoami(key).code)

    def test_wrong_secret_malformed_and_cross_user_rejected(self):
        user_id = self._make_user()
        other_id = self._make_user("other", is_admin=False)
        key = self._generate(user_id)
        secret = key.split(".", 1)[1]
        for bad in (
            f"{user_id}.wrong",
            f"{other_id}.{secret}",  # other user has no key
            f"99999.{secret}",
            secret,
            f"{user_id}.",
            ".x",
            "abc.def",
        ):
            self.assertEqual(401, self._whoami(bad).code, bad)

    def test_legacy_bcrypt_key_rejected(self):

        user_id = self._make_user()
        legacy = "legacy-secret-value"
        with self._app.get_db().sessionmaker() as session:
            session.get(User, user_id).api_token = bcrypt.hashpw(
                legacy.encode(), bcrypt.gensalt(4)
            ).decode()
            session.commit()
        self.assertEqual(401, self._whoami(legacy).code)
        self.assertEqual(401, self._whoami(f"{user_id}.{legacy}").code)

    def test_revoked_key_rejected(self):
        user_id = self._make_user()
        key = self._generate(user_id)
        with self._app.get_db().sessionmaker() as session:
            session.get(User, user_id).api_token = None
            session.commit()
        self.assertEqual(401, self._whoami(key).code)


class TestLegacyKeyMigration(TestCase):
    def test_upgrade_clears_api_tokens_and_creates_table(self):
        versions = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "alembic_config", "versions"
        )
        name = next(f for f in os.listdir(versions) if f.startswith("d91e929f2e32"))
        spec = importlib.util.spec_from_file_location(
            "wp3_migration", os.path.join(versions, name)
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as tmp:
            engine = sa.create_engine(f"sqlite:///{os.path.join(tmp, 'db.sqlite')}")
            with engine.begin() as conn:
                conn.execute(
                    sa.text(
                        "CREATE TABLE user (id INTEGER PRIMARY KEY, api_token TEXT)"
                    )
                )
                conn.execute(
                    sa.text(
                        "INSERT INTO user (id, api_token) VALUES (1, 'bcrypt-hash'), (2, NULL)"
                    )
                )
                ctx = MigrationContext.configure(conn)
                with Operations.context(ctx):
                    module.upgrade()
                tokens = conn.execute(
                    sa.text("SELECT api_token FROM user ORDER BY id")
                ).all()
                self.assertEqual([(None,), (None,)], [tuple(r) for r in tokens])
                self.assertIn("revoked_token", sa.inspect(conn).get_table_names())
            engine.dispose()
