from datetime import datetime

from sqlalchemy import func
from tornado import escape

from models.models import Show, Script, ScriptRevision, ScriptLine
from models.schemas import ScriptRevisionsSchema, ScriptLineSchema
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
                        self.finish({
                            'current_revision': script.current_revision,
                            'revisions': revisions
                        })
                    else:
                        self.set_status(404)
                        self.finish({'message': '404 script not found'})
                else:
                    self.set_status(404)
                    self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            self.write({'message': '404 show not found'})

    async def post(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            await self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    script: Script = session.query(Script).filter(Script.show_id == show.id).first()
                    if not script:
                        self.set_status(404)
                        await self.finish({'message': '404 script not found'})
                        return

                    current_rev_id = script.current_revision
                    if not current_rev_id:
                        self.set_status(404)
                        await self.finish({'message': '404 script revision not found'})
                        return

                    current_rev: ScriptRevision = session.query(ScriptRevision).get(current_rev_id)
                    if not current_rev:
                        self.set_status(404)
                        await self.finish({'message': '404 script revision not found'})
                        return

                    max_rev = session.query(func.max(ScriptRevision.revision)).filter(
                        ScriptRevision.script_id == script.id).one()[0]

                    description: str = data.get('description', None)
                    if not description:
                        self.set_status(400)
                        await self.finish({'message': 'Description missing'})
                        return

                    now_time = datetime.utcnow()
                    new_rev = ScriptRevision(script_id=script.id,
                                             revision=max_rev + 1,
                                             created_at=now_time,
                                             edited_at=now_time,
                                             description=description,
                                             previous_revision_id=current_rev.id)
                    new_rev.lines = current_rev.lines
                    session.add(new_rev)
                    session.flush()

                    script.current_revision = new_rev.id
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully added script revision'})
                    await self.application.ws_send_to_all('NOOP', 'GET_SCRIPT_REVISIONS', {})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})

    async def delete(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            await self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show: Show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    script: Script = session.query(Script).filter(Script.show_id == show.id).first()
                    if not script:
                        self.set_status(404)
                        await self.finish({'message': '404 script not found'})
                        return

                    rev_id: int = data.get('rev_id', None)
                    if not rev_id:
                        self.set_status(400)
                        await self.finish({'message': 'Revision missing'})
                        return

                    rev: ScriptRevision = session.query(ScriptRevision).get(rev_id)
                    if not rev:
                        self.set_status(404)
                        await self.finish({'message': 'Revision not found'})
                        return

                    if rev.script_id != script.id:
                        self.set_status(400)
                        await self.finish({'message': 'Revision is not for the current script'})
                        return

                    if rev.revision == 1:
                        self.set_status(400)
                        await self.finish({'message': 'Cannot delete first script revision'})
                        return

                    if script.current_revision == rev.id:
                        if rev.previous_revision_id:
                            script.current_revision = rev.previous_revision_id
                        else:
                            first_rev: ScriptRevision = session.query(ScriptRevision).filter(
                                ScriptRevision.script_id == script.id,
                                ScriptRevision.revision == 1).one()
                            script.current_revision = first_rev.id

                    session.delete(rev)
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully deleted script revision'})
                    await self.application.ws_send_to_all('NOOP', 'GET_SCRIPT_REVISIONS', {})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})


@ApiRoute('show/script/revisions/current', ApiVersion.v1)
class ScriptCurrentRevisionController(BaseAPIController):
    def get(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']

        if show_id:
            with self.make_session() as session:
                show: Show = session.query(Show).get(show_id)
                if show:
                    script: Script = session.query(Script).filter(Script.show_id == show.id).first()

                    if script:
                        self.set_status(200)
                        self.finish({
                            'current_revision': script.current_revision,
                        })
                    else:
                        self.set_status(404)
                        self.finish({'message': '404 script not found'})
                else:
                    self.set_status(404)
                    self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            self.write({'message': '404 show not found'})

    async def post(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            await self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']
        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    data = escape.json_decode(self.request.body)

                    script: Script = session.query(Script).filter(Script.show_id == show.id).first()
                    if not script:
                        self.set_status(404)
                        await self.finish({'message': '404 script not found'})
                        return

                    new_rev_id: int = data.get('new_rev_id', None)
                    if not new_rev_id:
                        self.set_status(400)
                        await self.finish({'message': 'New revision missing'})
                        return

                    new_rev: ScriptRevision = session.query(ScriptRevision).get(new_rev_id)
                    if not new_rev:
                        self.set_status(404)
                        await self.finish({'message': 'New revision not found'})
                        return

                    if new_rev.script_id != script.id:
                        self.set_status(400)
                        await self.finish({'message': 'New revision is not for the current script'})
                        return

                    script.current_revision = new_rev.id
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully changed script revision'})
                    await self.application.ws_send_to_all('NOOP', 'GET_SCRIPT_REVISIONS', {})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})


@ApiRoute('/show/script', ApiVersion.v1)
class ScriptController(BaseAPIController):

    def get(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']

        page = self.get_query_argument('page', None)
        if not page:
            self.set_status(400)
            self.finish({'message': 'Page not given'})
            return
        else:
            page = int(page)

        line_schema = ScriptLineSchema()

        if show_id:
            if show_id:
                with self.make_session() as session:
                    show = session.query(Show).get(show_id)
                    if show:
                        script: Script = session.query(Script).filter(Script.show_id == show.id).first()

                        if script.current_revision:
                            revision: ScriptRevision = session.query(ScriptRevision).get(script.current_revision)
                        else:
                            self.set_status(400)
                            self.finish({'message': 'Script does not have a current revision'})
                            return
                        lines = session.query(ScriptLine).filter(
                            ScriptLine.page == page, ScriptLine.revisions.contains(revision)).all()
                        lines = [line_schema.dump(line) for line in lines]

                        self.set_status(200)
                        self.finish({'lines': lines, 'page': page})
                    else:
                        self.set_status(404)
                        self.finish({'message': '404 show not found'})
                        return
            else:
                self.set_status(404)
                self.finish({'message': '404 show not found'})
                return
