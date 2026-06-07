from typing import List

from sqlalchemy import select

from models.session import Session
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion


@ApiRoute("show/script/config", ApiVersion.V1)
class ScriptStatusController(BaseAPIController):
    def get(self):
        with self.make_session() as session:
            editors: List[Session] = session.scalars(
                select(Session).where(Session.is_editor)
            ).all()
            if editors:
                current_editor = editors[0].internal_id
            else:
                current_editor = None

            data = {
                "canRequestEdit": len(editors) == 0,
                "currentEditor": current_editor,
            }

            self.set_status(200)
            self.finish(data)
