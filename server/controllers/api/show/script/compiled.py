import os
from typing import Optional

from sqlalchemy import select
from tornado import escape

from controllers.api.constants import (
    ERROR_SCRIPT_REVISION_NOT_FOUND,
    ERROR_SHOW_NOT_FOUND,
)
from digi_server.logger import get_logger
from models.script import CompiledScript, Script, ScriptRevision
from models.show import Show
from rbac.role import Role
from schemas.schemas import CompiledScriptSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import requires_show


@ApiRoute("show/script/compiled_scripts", ApiVersion.V1)
class CompiledScriptsController(BaseAPIController):
    @requires_show
    def get(self):
        schema = CompiledScriptSchema()
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return

            stmt = (
                select(CompiledScript)
                .join(
                    ScriptRevision,
                    onclause=CompiledScript.revision_id == ScriptRevision.id,
                )
                .join(Script, onclause=Script.id == ScriptRevision.script_id)
                .join(Show, onclause=Show.id == Script.show_id)
                .where(Show.id == show_id)
            )
            compiled_scripts = session.scalars(stmt).all()
            compiled_scripts = [schema.dump(c) for c in compiled_scripts]
            self.set_status(200)
            self.finish({"scripts": compiled_scripts})

    @requires_show
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return
            self.requires_role(show, Role.WRITE)

            data = escape.json_decode(self.request.body)
            revision_id = data.get("revision_id")
            if not revision_id:
                self.set_status(400)
                await self.finish({"message": "400 revision_id is required"})
                return

            revision = session.get(ScriptRevision, revision_id)
            if not revision or revision.script.show_id != show_id:
                self.set_status(404)
                await self.finish({"message": ERROR_SCRIPT_REVISION_NOT_FOUND})
                return

            await CompiledScript.compile_script(self.application, revision.id)
            self.set_status(200)
            await self.finish({})

    @requires_show
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return
            self.requires_role(show, Role.WRITE)

            revision_id = self.get_query_argument("revision_id", None)
            if not revision_id:
                self.set_status(400)
                await self.finish({"message": "400 revision_id is required"})
                return
            try:
                revision_id = int(revision_id)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": "400 revision_id must be an integer"})
                return
            revision = session.get(ScriptRevision, revision_id)
            if not revision or revision.script.show_id != show_id:
                self.set_status(404)
                await self.finish({"message": ERROR_SCRIPT_REVISION_NOT_FOUND})
                return

            compiled_script: Optional[CompiledScript] = session.scalars(
                select(CompiledScript).where(CompiledScript.revision_id == revision.id)
            ).first()
            if not compiled_script:
                self.set_status(404)
                await self.finish({"message": "404 compiled script not found"})
                return

            try:
                os.remove(compiled_script.data_path)
            except Exception:
                get_logger().exception(
                    f"Failed to remove compiled script file: {compiled_script.data_path}"
                )
            finally:
                session.delete(compiled_script)
                session.commit()

            self.set_status(200)
            await self.application.ws_send_to_all("NOOP", "GET_COMPILED_SCRIPTS", {})
            await self.finish({})
