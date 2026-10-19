"""Tests for the ``collaborative_script_editing`` mode setting.

The setting switches the whole server between the classic (REST, single-editor)
script editor and the collaborative (shared draft) one. The server enforces it, so a
client on the wrong side of the switch is refused cleanly instead of being allowed to
edit and then losing its work at save time.
"""

import base64
import json

import pycrdt
import tornado.escape
from sqlalchemy import select
from tornado.testing import gen_test

from controllers.api.constants import (
    ERROR_COLLAB_EDITING_DISABLED,
    ERROR_COLLAB_EDITING_ENABLED,
    ERROR_COLLAB_MODE_CHANGE_BLOCKED,
    ERROR_EDIT_BLOCKED_BY_EDITOR,
)
from models.script_draft import ScriptDraft
from models.session import Session
from models.user import User
from test.conftest import DigiScriptTestCase
from test.controllers.test_ws_controller import _WSTestHelpers
from test.helpers.script_fixtures import create_show_script_revision


MODE = "collaborative_script_editing"

COLLAB_ONLY_OPS = (
    "JOIN_SCRIPT_ROOM",
    "YJS_SYNC",
    "YJS_UPDATE",
    "YJS_AWARENESS",
    "SAVE_SCRIPT_DRAFT",
    "DISCARD_SCRIPT_DRAFT",
)


class _ModeFixture:
    """Show + script + admin, with the mode switched via ``_set_mode``."""

    def _create_fixture(self):
        with self._app.get_db().sessionmaker() as session:
            admin = User(username="admin", password="hashed", is_admin=True)
            session.add(admin)
            session.flush()
            self.admin_id = admin.id
            show, _script, revision = create_show_script_revision(session)
            self.show_id = show.id
            self.revision_id = revision.id
            session.commit()
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.admin_id}
        )

    def _set_mode(self, enabled: bool):
        self._app.digi_settings.settings[MODE].set_value(enabled)


class TestModeSettingDefinition(DigiScriptTestCase):
    def test_defaults_to_classic_editing_and_is_admin_editable(self):
        setting = self._app.digi_settings.settings[MODE]

        self.assertIs(False, setting.default)
        self.assertIs(False, setting.get_value())
        self.assertEqual(bool, setting.val_type)
        self.assertTrue(setting.can_edit)

    def test_is_hidden_from_the_settings_page_until_the_editor_exists(self):
        """Switching it on now would leave no client able to edit the script."""
        self.assertTrue(self._app.digi_settings.settings[MODE].hide_from_ui)

    def test_get_sync_reads_the_current_value_and_rejects_unknown_keys(self):
        settings = self._app.digi_settings
        self.assertIs(False, settings.get_sync(MODE))
        settings.settings[MODE].set_value(True)
        self.assertIs(True, settings.get_sync(MODE))
        with self.assertRaises(KeyError):
            settings.get_sync("no_such_setting")


class TestModeEnforcementWS(_WSTestHelpers, _ModeFixture, DigiScriptTestCase):
    def setUp(self):
        super().setUp()
        self._create_fixture()

    async def _request_edit(self, ws, **data):
        await ws.write_message(json.dumps({"OP": "REQUEST_SCRIPT_EDIT", "DATA": data}))
        return json.loads(await ws.read_message())

    # ---- classic (default) mode ----

    @gen_test
    async def test_classic_mode_rejects_every_collab_op_and_opens_no_room(self):
        ws, _ = await self._connect_and_auth(self.admin_id)

        for op in COLLAB_ONLY_OPS:
            await ws.write_message(json.dumps({"OP": op, "DATA": {}}))
            response = json.loads(await ws.read_message())
            self.assertEqual("COLLAB_ERROR", response["ACTION"], op)
            self.assertEqual(ERROR_COLLAB_EDITING_DISABLED, response["DATA"]["error"])

        self.assertIsNone(self._app.room_manager.get_active_room())
        ws.close()

    @gen_test
    async def test_classic_mode_accepts_an_unflagged_edit_request(self):
        ws, _ = await self._connect_and_auth(self.admin_id)

        response = await self._request_edit(ws)

        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response["ACTION"])
        with self._app.get_db().sessionmaker() as session:
            self.assertEqual(
                1, len(session.scalars(select(Session).where(Session.is_editor)).all())
            )
        ws.close()

    @gen_test
    async def test_classic_mode_refuses_the_collaborative_editors_request(self):
        ws, _ = await self._connect_and_auth(self.admin_id)

        response = await self._request_edit(ws, collab=True)

        self.assertEqual("REQUEST_EDIT_FAILURE", response["ACTION"])
        self.assertEqual(ERROR_COLLAB_EDITING_DISABLED, response["DATA"]["reason"])
        with self._app.get_db().sessionmaker() as session:
            self.assertEqual(
                0, len(session.scalars(select(Session).where(Session.is_editor)).all())
            )
        ws.close()

    @gen_test
    async def test_classic_mode_is_single_editor_again(self):
        """Classic REST editing can't reconcile concurrent writers."""
        with self._app.get_db().sessionmaker() as session:
            session.add(
                Session(
                    internal_id="someone-else", user_id=self.admin_id, is_editor=True
                )
            )
            session.commit()
        ws, _ = await self._connect_and_auth(self.admin_id)

        response = await self._request_edit(ws)

        self.assertEqual("REQUEST_EDIT_FAILURE", response["ACTION"])
        self.assertEqual(ERROR_EDIT_BLOCKED_BY_EDITOR, response["DATA"]["reason"])
        ws.close()

    @gen_test
    async def test_classic_mode_lets_the_current_editor_ask_again(self):
        ws, _ = await self._connect_and_auth(self.admin_id)
        await self._request_edit(ws)

        response = await self._request_edit(ws)

        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response["ACTION"])
        ws.close()

    # ---- collaborative mode ----

    @gen_test
    async def test_collaborative_mode_refuses_an_unflagged_edit_request(self):
        """An old-UI client must be stopped before it starts an edit it would lose."""
        self._set_mode(True)
        ws, _ = await self._connect_and_auth(self.admin_id)

        response = await self._request_edit(ws)

        self.assertEqual("REQUEST_EDIT_FAILURE", response["ACTION"])
        self.assertEqual(ERROR_COLLAB_EDITING_ENABLED, response["DATA"]["reason"])
        with self._app.get_db().sessionmaker() as session:
            self.assertEqual(
                0, len(session.scalars(select(Session).where(Session.is_editor)).all())
            )
        ws.close()

    @gen_test
    async def test_collaborative_mode_needs_a_real_boolean_flag(self):
        """`collab: 1` or `"true"` is truthy but is not the editor announcing itself."""
        self._set_mode(True)
        ws, _ = await self._connect_and_auth(self.admin_id)

        for flag in (1, "true", None):
            response = await self._request_edit(ws, collab=flag)
            self.assertEqual("REQUEST_EDIT_FAILURE", response["ACTION"], flag)
            self.assertEqual(
                ERROR_COLLAB_EDITING_ENABLED, response["DATA"]["reason"], flag
            )
        ws.close()

    @gen_test
    async def test_collaborative_mode_accepts_the_flagged_request_from_several_users(
        self,
    ):
        self._set_mode(True)
        with self._app.get_db().sessionmaker() as session:
            session.add(
                Session(
                    internal_id="someone-else", user_id=self.admin_id, is_editor=True
                )
            )
            session.commit()
        ws, _ = await self._connect_and_auth(self.admin_id)

        response = await self._request_edit(ws, collab=True)

        self.assertEqual("GET_SCRIPT_CONFIG_STATUS", response["ACTION"])
        ws.close()

    # ---- server-owned trailing page ----

    async def _join_and_sync(self, ws):
        """Enter edit mode, join the room, and return a replica of the synced doc."""
        await self._request_edit(ws, collab=True)
        await ws.write_message(json.dumps({"OP": "JOIN_SCRIPT_ROOM", "DATA": {}}))
        sync = json.loads(await ws.read_message())
        await ws.read_message()  # ROOM_MEMBERS
        await ws.read_message()  # GET_SCRIPT_CONFIG_STATUS from the join

        replica = pycrdt.Doc()
        replica.get("meta", type=pycrdt.Map)
        replica.get("pages", type=pycrdt.Map)
        replica.get("deleted_line_ids", type=pycrdt.Array)
        replica.apply_update(base64.b64decode(sync["DATA"]["payload"]))
        return replica

    @gen_test
    async def test_joining_gives_an_empty_script_a_page_to_write_into(self):
        self._set_mode(True)
        ws, _ = await self._connect_and_auth(self.admin_id)

        replica = await self._join_and_sync(ws)

        pages = replica.get("pages", type=pycrdt.Map)
        self.assertEqual(["1"], list(pages.keys()))
        self.assertEqual(0, len(pages["1"]))
        ws.close()

    @gen_test
    async def test_filling_the_last_page_makes_the_server_add_the_next_one(self):
        self._set_mode(True)
        ws, _ = await self._connect_and_auth(self.admin_id)
        replica = await self._join_and_sync(ws)

        before = replica.get_state()
        replica.get("pages", type=pycrdt.Map)["1"].append(pycrdt.Map())
        payload = base64.b64encode(replica.get_update(before)).decode("ascii")
        await ws.write_message(
            json.dumps({"OP": "YJS_UPDATE", "DATA": {"payload": payload}})
        )

        # The sender is excluded from the relay of its own update, so the only thing
        # it receives is the server-made follow-up — which must reach it too.
        follow_up = json.loads(await ws.read_message())
        self.assertEqual("YJS_UPDATE", follow_up["ACTION"])
        replica.apply_update(base64.b64decode(follow_up["DATA"]["payload"]))
        pages = replica.get("pages", type=pycrdt.Map)
        self.assertEqual(["1", "2"], sorted(pages.keys()))
        self.assertEqual(0, len(pages["2"]))
        ws.close()

    @gen_test
    async def test_a_second_editor_also_receives_the_new_trailing_page(self):
        self._set_mode(True)
        ws1, _ = await self._connect_and_auth(self.admin_id)
        replica = await self._join_and_sync(ws1)
        ws2, _ = await self._connect_and_auth(self.admin_id)
        replica2 = await self._join_and_sync(ws2)
        await ws1.read_message()  # ROOM_MEMBERS for the second join

        before = replica.get_state()
        replica.get("pages", type=pycrdt.Map)["1"].append(pycrdt.Map())
        payload = base64.b64encode(replica.get_update(before)).decode("ascii")
        await ws1.write_message(
            json.dumps({"OP": "YJS_UPDATE", "DATA": {"payload": payload}})
        )

        for _ in range(2):  # the relayed edit, then the server's follow-up
            message = json.loads(await ws2.read_message())
            self.assertEqual("YJS_UPDATE", message["ACTION"])
            replica2.apply_update(base64.b64decode(message["DATA"]["payload"]))
        self.assertEqual(
            ["1", "2"], sorted(replica2.get("pages", type=pycrdt.Map).keys())
        )
        ws1.close()
        ws2.close()

    # ---- page notifications after a save ----

    @gen_test
    async def test_saving_a_new_line_announces_exactly_its_page(self):
        """The positive half: a page that changed is announced, the trailing page
        the server added (nothing written to it) is not."""
        self._set_mode(True)
        ws, _ = await self._connect_and_auth(self.admin_id)
        replica = await self._join_and_sync(ws)

        before = replica.get_state()
        page = replica.get("pages", type=pycrdt.Map)["1"]
        line = pycrdt.Map()
        page.append(line)
        line["_id"] = line["_uid"] = "line-uuid"
        for key in ("act_id", "scene_id", "stage_direction_style_id"):
            line[key] = 0
        line["line_type"] = 2  # STAGE_DIRECTION: exactly one non-empty part
        line["parts"] = pycrdt.Array()
        part = pycrdt.Map()
        line["parts"].append(part)
        part["_id"] = part["_uid"] = "part-uuid"
        part["part_index"] = 0
        part["character_id"] = part["character_group_id"] = 0
        part["line_text"] = pycrdt.Text("Enter stage left")
        payload = base64.b64encode(replica.get_update(before)).decode("ascii")
        await ws.write_message(
            json.dumps({"OP": "YJS_UPDATE", "DATA": {"payload": payload}})
        )
        await ws.write_message(json.dumps({"OP": "SAVE_SCRIPT_DRAFT", "DATA": {}}))

        changed = []
        for _ in range(25):
            message = json.loads(await ws.read_message())
            if message["ACTION"] == "SCRIPT_PAGE_CHANGED":
                changed.append(message["DATA"]["page"])
            if message["ACTION"] == "GET_SCRIPT_REVISIONS":
                break

        self.assertEqual([1], changed)
        ws.close()

    @gen_test
    async def test_saving_names_only_the_pages_it_changed(self):
        """Nothing was written, so no page is announced: naming every page of a long
        script would make every client reload every cached page after each save.
        (`changed_pages` itself is covered against a real DB in test_ydoc_to_lines.)"""
        self._set_mode(True)
        ws, _ = await self._connect_and_auth(self.admin_id)
        await self._join_and_sync(ws)

        await ws.write_message(json.dumps({"OP": "SAVE_SCRIPT_DRAFT", "DATA": {}}))
        changed = []
        for _ in range(12):
            message = json.loads(await ws.read_message())
            if message["ACTION"] == "SCRIPT_PAGE_CHANGED":
                changed.append(message["DATA"]["page"])
            if message["ACTION"] == "GET_SCRIPT_REVISIONS":
                break

        self.assertEqual([], changed)
        ws.close()


class TestModeEnforcementREST(_ModeFixture, DigiScriptTestCase):
    def setUp(self):
        super().setUp()
        self._create_fixture()

    def _write(self, method):
        return self.fetch(
            "/api/v1/show/script?page=1",
            method=method,
            body=tornado.escape.json_encode(
                [] if method == "POST" else {"page": [], "status": {}}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def test_classic_mode_does_not_block_rest_script_writes(self):
        for method in ("POST", "PATCH"):
            response = self._write(method)
            self.assertEqual(200, response.code, method)

    def test_collaborative_mode_refuses_rest_script_writes(self):
        self._set_mode(True)

        for method in ("POST", "PATCH"):
            response = self._write(method)
            self.assertEqual(409, response.code, method)
            self.assertEqual(
                ERROR_COLLAB_EDITING_ENABLED,
                tornado.escape.json_decode(response.body)["message"],
            )

    def test_collaborative_mode_leaves_reading_the_script_alone(self):
        self._set_mode(True)

        response = self.fetch(
            "/api/v1/show/script?page=1",
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertNotEqual(409, response.code)


class TestModeChangeGuard(_ModeFixture, DigiScriptTestCase):
    def setUp(self):
        super().setUp()
        self._create_fixture()

    def _patch(self, **settings):
        return self.fetch(
            "/api/v1/settings",
            method="PATCH",
            body=tornado.escape.json_encode(settings),
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def _add_session(self, **flags):
        with self._app.get_db().sessionmaker() as session:
            session.add(Session(internal_id="busy", user_id=self.admin_id, **flags))
            session.commit()

    def _assert_refused(self, response):
        self.assertEqual(409, response.code)
        self.assertEqual(
            ERROR_COLLAB_MODE_CHANGE_BLOCKED,
            tornado.escape.json_decode(response.body)["message"],
        )
        self.assertIs(False, self._app.digi_settings.settings[MODE].get_value())

    def test_can_switch_when_nobody_is_editing(self):
        response = self._patch(**{MODE: True})

        self.assertEqual(200, response.code)
        self.assertIs(True, self._app.digi_settings.settings[MODE].get_value())

    def test_refused_while_someone_is_editing(self):
        self._add_session(is_editor=True)

        self._assert_refused(self._patch(**{MODE: True}))

    def test_refused_while_someone_is_cutting(self):
        self._add_session(is_cutting=True)

        self._assert_refused(self._patch(**{MODE: True}))

    def test_refused_while_an_unsaved_draft_exists(self):
        with self._app.get_db().sessionmaker() as session:
            session.add(ScriptDraft(revision_id=self.revision_id, data_path="x"))
            session.commit()

        self._assert_refused(self._patch(**{MODE: True}))

    def test_refused_while_a_room_has_clients(self):
        class _Room:
            is_empty = False
            _dirty = False

        self._app.room_manager._room = _Room()

        self._assert_refused(self._patch(**{MODE: True}))

    def test_a_non_boolean_value_is_a_400_not_a_500(self):
        for value in ("true", 1, None):
            response = self._patch(**{MODE: value})
            self.assertEqual(400, response.code, value)
        self.assertIs(False, self._app.digi_settings.settings[MODE].get_value())

    def test_a_bad_value_anywhere_in_the_batch_applies_nothing(self):
        """The mode key is written first, so a later bad value must not leave the
        mode flipped behind a failed request."""
        response = self._patch(**{MODE: True, "debug_mode": "not a bool"})

        self.assertEqual(400, response.code)
        self.assertIs(False, self._app.digi_settings.settings[MODE].get_value())

    def test_the_mode_key_is_written_before_the_other_keys(self):
        order = []
        original = self._app.digi_settings.set

        async def recording_set(key, value):
            order.append(key)
            return await original(key, value)

        self._app.digi_settings.set = recording_set
        response = self._patch(debug_mode=True, **{MODE: True})

        self.assertEqual(200, response.code)
        self.assertEqual([MODE, "debug_mode"], order)

    def test_setting_the_same_value_is_always_allowed(self):
        self._add_session(is_editor=True)

        response = self._patch(**{MODE: False})

        self.assertEqual(200, response.code)

    def test_other_settings_are_not_blocked_while_editing(self):
        self._add_session(is_editor=True)

        response = self._patch(debug_mode=True)

        self.assertEqual(200, response.code)

    def test_a_refused_change_applies_none_of_the_batch(self):
        self._add_session(is_editor=True)

        response = self._patch(**{MODE: True, "debug_mode": True})

        self.assertEqual(409, response.code)
        self.assertIs(False, self._app.digi_settings.settings["debug_mode"].get_value())
