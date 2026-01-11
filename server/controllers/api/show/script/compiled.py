from sqlalchemy import select

from models.script import CompiledScript, Script, ScriptRevision
from models.show import Show
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
                self.finish({"message": "404 show not found"})
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
            self.finish({"acts": compiled_scripts})
