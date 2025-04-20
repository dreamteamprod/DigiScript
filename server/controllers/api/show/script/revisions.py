from datetime import datetime

from sqlalchemy import func
from tornado import escape

from models.cue import CueAssociation
from models.script import (
    Script,
    ScriptCuts,
    ScriptLineRevisionAssociation,
    ScriptRevision,
)
from models.show import Show
from rbac.role import Role
from schemas.schemas import ScriptRevisionsSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/script/revisions", ApiVersion.V1)
class ScriptRevisionsController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        revisions_schema = ScriptRevisionsSchema()

        with self.make_session() as session:
            show: Show = session.query(Show).get(show_id)
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )

                if script:
                    revisions = [revisions_schema.dump(c) for c in script.revisions]
                    self.set_status(200)
                    self.finish(
                        {
                            "current_revision": script.current_revision,
                            "revisions": revisions,
                        }
                    )
                else:
                    self.set_status(404)
                    self.finish({"message": "404 script not found"})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                data = escape.json_decode(self.request.body)

                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )
                if not script:
                    self.set_status(404)
                    await self.finish({"message": "404 script not found"})
                    return
                self.requires_role(script, Role.WRITE)

                current_rev_id = script.current_revision
                if not current_rev_id:
                    self.set_status(404)
                    await self.finish({"message": "404 script revision not found"})
                    return

                current_rev: ScriptRevision = session.query(ScriptRevision).get(
                    current_rev_id
                )
                if not current_rev:
                    self.set_status(404)
                    await self.finish({"message": "404 script revision not found"})
                    return

                max_rev = (
                    session.query(func.max(ScriptRevision.revision))
                    .filter(ScriptRevision.script_id == script.id)
                    .one()[0]
                )

                description: str = data.get("description", None)
                if not description:
                    self.set_status(400)
                    await self.finish({"message": "Description missing"})
                    return

                now_time = datetime.utcnow()
                new_rev = ScriptRevision(
                    script_id=script.id,
                    revision=max_rev + 1,
                    created_at=now_time,
                    edited_at=now_time,
                    description=description,
                    previous_revision_id=current_rev.id,
                )
                session.add(new_rev)
                session.flush()
                for line_association in current_rev.line_associations:
                    new_rev.line_associations.append(
                        ScriptLineRevisionAssociation(
                            revision_id=new_rev.id,
                            line_id=line_association.line_id,
                            next_line_id=line_association.next_line_id,
                            previous_line_id=line_association.previous_line_id,
                        )
                    )
                for cue_association in current_rev.cue_associations:
                    new_rev.cue_associations.append(
                        CueAssociation(
                            revision_id=new_rev.id,
                            line_id=cue_association.line_id,
                            cue_id=cue_association.cue_id,
                        )
                    )
                for cut_association in current_rev.line_part_cuts:
                    new_rev.line_part_cuts.append(
                        ScriptCuts(
                            revision_id=new_rev.id,
                            line_part_id=cut_association.line_part_id,
                        )
                    )

                script.current_revision = new_rev.id
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"id": new_rev.id, "message": "Successfully added script revision"}
                )
                await self.application.ws_send_to_all(
                    "NOOP", "GET_SCRIPT_REVISIONS", {}
                )
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.query(Show).get(show_id)
            if show:
                data = escape.json_decode(self.request.body)

                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )
                if not script:
                    self.set_status(404)
                    await self.finish({"message": "404 script not found"})
                    return
                self.requires_role(script, Role.WRITE)

                rev_id: int = data.get("rev_id", None)
                if not rev_id:
                    self.set_status(400)
                    await self.finish({"message": "Revision missing"})
                    return

                rev: ScriptRevision = session.query(ScriptRevision).get(rev_id)
                if not rev:
                    self.set_status(404)
                    await self.finish({"message": "Revision not found"})
                    return

                if rev.script_id != script.id:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Revision is not for the current script"}
                    )
                    return

                if rev.revision == 1:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Cannot delete first script revision"}
                    )
                    return

                changed_rev = False
                if script.current_revision == rev.id:
                    changed_rev = True
                    if rev.previous_revision_id:
                        script.current_revision = rev.previous_revision_id
                    else:
                        first_rev: ScriptRevision = (
                            session.query(ScriptRevision)
                            .filter(
                                ScriptRevision.script_id == script.id,
                                ScriptRevision.revision == 1,
                            )
                            .one()
                        )
                        script.current_revision = first_rev.id

                session.delete(rev)
                session.commit()

                self.set_status(200)
                await self.finish({"message": "Successfully deleted script revision"})
                if changed_rev:
                    await self.application.ws_send_to_all(
                        "NOOP", "SCRIPT_REVISION_CHANGED", {}
                    )
                else:
                    await self.application.ws_send_to_all(
                        "NOOP", "GET_SCRIPT_REVISIONS", {}
                    )
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


@ApiRoute("show/script/revisions/current", ApiVersion.V1)
class ScriptCurrentRevisionController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.query(Show).get(show_id)
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )

                if script:
                    self.set_status(200)
                    self.finish(
                        {
                            "current_revision": script.current_revision,
                        }
                    )
                else:
                    self.set_status(404)
                    self.finish({"message": "404 script not found"})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )
                if not script:
                    self.set_status(404)
                    await self.finish({"message": "404 script not found"})
                    return

                new_rev_id: int = data.get("new_rev_id", None)
                if not new_rev_id:
                    self.set_status(400)
                    await self.finish({"message": "New revision missing"})
                    return

                new_rev: ScriptRevision = session.query(ScriptRevision).get(new_rev_id)
                if not new_rev:
                    self.set_status(404)
                    await self.finish({"message": "New revision not found"})
                    return

                if new_rev.script_id != script.id:
                    self.set_status(400)
                    await self.finish(
                        {"message": "New revision is not for the current script"}
                    )
                    return

                script.current_revision = new_rev.id
                session.commit()

                self.set_status(200)
                await self.finish({"message": "Successfully changed script revision"})
                await self.application.ws_send_to_all(
                    "NOOP", "SCRIPT_REVISION_CHANGED", {}
                )
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
