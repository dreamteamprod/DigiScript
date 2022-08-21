from models.models import Show, Script
from models.schemas import ScriptRevisionsSchema
from utils.base_controller import BaseAPIController
from utils.route import ApiRoute, ApiVersion


@ApiRoute('show/script/revisions', ApiVersion.v1)
class ScriptRevisionsController(BaseAPIController):

    def get(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']
        revisions_schema = ScriptRevisionsSchema()

        if show_id:
            with self.make_session() as session:
                show: Show = session.query(Show).get(show_id)
                if show:
                    script: Script = session.query(Script).filter(Script.show_id == show.id).first()

                    if script:
                        revisions = [revisions_schema.dump(c) for c in script.revisions]
                        self.set_status(200)
                        self.finish({'revisions': revisions})
                    else:
                        self.set_status(404)
                        self.finish({'message': '404 script not found'})
                else:
                    self.set_status(404)
                    self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            self.write({'message': '404 show not found'})