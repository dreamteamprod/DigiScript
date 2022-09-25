from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from tornado import escape

from models.models import (Show, Script, ScriptRevision, ScriptLine, Session, ScriptLinePart,
                           ScriptLineRevisionAssociation)
from models.schemas import ScriptRevisionsSchema, ScriptLineSchema
from utils.base_controller import BaseAPIController
from utils.route import ApiRoute, ApiVersion


@ApiRoute('show/script/config', ApiVersion.v1)
class ScriptStatusController(BaseAPIController):
    def get(self):
        with self.make_session() as session:
            editors: List[Session] = session.query(Session).filter(Session.is_editor).all()
            if editors:
                current_editor = editors[0].internal_id
            else:
                current_editor = None

            data = {
                'canRequestEdit': len(editors) == 0,
                'currentEditor': current_editor
            }

            self.set_status(200)
            self.finish(data)


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
                    session.add(new_rev)
                    session.flush()
                    for line_association in current_rev.line_associations:
                        new_rev.line_associations.append(ScriptLineRevisionAssociation(
                            revision_id=new_rev.id,
                            line_id=line_association.line_id,
                            next_line_id=line_association.next_line_id,
                            previous_line_id=line_association.previous_line_id
                        ))

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

                    revision_lines: List[ScriptLineRevisionAssociation] = session.query(
                        ScriptLineRevisionAssociation).filter(
                        ScriptLineRevisionAssociation.revision_id == revision.id,
                        ScriptLineRevisionAssociation.line.has(page=page)).all()

                    first_line = None
                    for line in revision_lines:
                        if page == 1 and line.previous_line is None or line.previous_line.page == page - 1:
                            if first_line:
                                self.set_status(400)
                                self.finish({'message': 'Failed to establish page line order'})
                                return
                            else:
                                first_line = line

                    lines = []
                    line_revision = first_line
                    while line_revision:
                        if line_revision.line.page != page:
                            break
                        else:
                            lines.append(line_schema.dump(line_revision.line))
                            line_revision = session.query(ScriptLineRevisionAssociation).get(
                                {'revision_id': revision.id, 'line_id': line_revision.next_line_id})

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

    async def post(self):
        current_show = self.get_current_show()

        if not current_show:
            self.set_status(400)
            await self.finish({'message': 'No show loaded'})
            return

        show_id = current_show['id']

        page = self.get_query_argument('page', None)
        if not page:
            self.set_status(400)
            await self.finish({'message': 'Page not given'})
            return
        else:
            page = int(page)

        if show_id:
            with self.make_session() as session:
                show = session.query(Show).get(show_id)
                if show:
                    script: Script = session.query(Script).filter(Script.show_id == show.id).first()

                    if script.current_revision:
                        revision: ScriptRevision = session.query(ScriptRevision).get(script.current_revision)
                    else:
                        self.set_status(400)
                        await self.finish({'message': 'Script does not have a current revision'})
                        return

                    lines = escape.json_decode(self.request.body)

                    previous_line: Optional[ScriptLineRevisionAssociation] = None
                    for index, line in enumerate(lines):
                        # Create the initial line object, and flush it to the database as we need the ID for further
                        # in the loop
                        line_obj = ScriptLine(act_id=line['act_id'],
                                              scene_id=line['scene_id'],
                                              page=line['page'])
                        session.add(line_obj)
                        session.flush()

                        # Line revision object to keep track of that thing
                        line_revision = ScriptLineRevisionAssociation(revision_id=revision.id,
                                                                      line_id=line_obj.id)
                        session.add(line_revision)
                        session.flush()

                        if index == 0 and page > 1:
                            # First line and not the first page, so need to get the last line of the previous page and
                            # set its next line to this one
                            prev_page_lines: List[ScriptLineRevisionAssociation] = session.query(
                                ScriptLineRevisionAssociation).filter(
                                ScriptLineRevisionAssociation.revision_id == revision.id,
                                ScriptLineRevisionAssociation.line.has(page=page - 1)).all()

                            if not prev_page_lines:
                                self.set_status(400)
                                await self.finish({'message': 'Previous page does not contain any lines'})
                                return

                            # Perform some iteration here to establish the first line of the script of the previous page
                            first_line = None
                            for prev_line in prev_page_lines:
                                if (prev_line.previous_line is None or
                                        prev_line.previous_line.page == prev_line.line.page - 1):
                                    if first_line:
                                        self.set_status(400)
                                        await self.finish({'message': 'Failed to establish page line order for '
                                                                      'previous page'})
                                        return
                                    else:
                                        first_line = prev_line

                            # Construct an ordered list of lines, because we need to get the last line of a page, and
                            # right now there is no better way of doing it
                            previous_lines = []
                            prev_line = first_line
                            while prev_line:
                                if prev_line.line.page != page - 1:
                                    break
                                else:
                                    previous_lines.append(prev_line)
                                    prev_line = session.query(ScriptLineRevisionAssociation).get(
                                        {'revision_id': revision.id, 'line_id': prev_line.next_line_id})

                            previous_lines[-1].next_line_id = line_obj.id
                            line_revision.previous_line_id = previous_lines[-1].line_id
                            session.flush()

                        # Set the next and previous line reference
                        if previous_line:
                            previous_line.next_line = line_obj
                            line_revision.previous_line = previous_line.line
                            session.flush()

                        # Construct the line part objects and add these to the line itself
                        for line_part in line['line_parts']:
                            part_obj = ScriptLinePart(line_id=line_obj.id,
                                                      part_index=line_part['part_index'],
                                                      character_id=line_part['character_id'],
                                                      character_group_id=line_part['character_group_id'],
                                                      line_text=line_part['line_text'])
                            session.add(part_obj)
                            line_obj.line_parts.append(part_obj)

                        # Flush once more at the end of the loop iteration (not for luck, I promise...!) to ensure
                        # the database is up-to-date for the next time around
                        session.flush()

                        previous_line = line_revision

                    # Update the revision edit time
                    revision.edited_at = datetime.utcnow()

                    # Save everything to the DB
                    session.commit()
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 show not found'})
                    return
        else:
            self.set_status(404)
            await self.finish({'message': '404 show not found'})
            return
