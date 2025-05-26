from tornado import escape

from models.script import Script, ScriptRevision
from models.show import Show
from rbac.role import Role
from utils.compression import decompress_script_data
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import requires_show


@ApiRoute("show/script/compressed", ApiVersion.V1)
class ScriptCompressedController(BaseAPIController):
    """Controller for retrieving compressed script data."""

    @requires_show
    def get(self):
        """Get the compressed script data for the current revision."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                script = session.query(Script).filter(Script.show_id == show.id).first()

                if not script:
                    self.set_status(404)
                    self.finish({"message": "404 script not found"})
                    return

                if not script.current_revision:
                    self.set_status(400)
                    self.finish({"message": "Script does not have a current revision"})
                    return

                revision = session.query(ScriptRevision).get(script.current_revision)
                if not revision:
                    self.set_status(404)
                    self.finish({"message": "404 revision not found"})
                    return

                if not revision.compressed_data:
                    self.set_status(200)
                    self.finish({"compressed_data": None})
                    return

                self.set_status(200)
                self.finish({"compressed_data": revision.compressed_data})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})
