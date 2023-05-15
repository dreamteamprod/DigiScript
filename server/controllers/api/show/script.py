from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from tornado import escape

from models.cue import CueAssociation
from models.script import (Script, ScriptRevision, ScriptLine, ScriptLineRevisionAssociation,
                           ScriptLinePart)
from models.show import Show
from models.session import Session
from rbac.role import Role
from schemas.schemas import ScriptRevisionsSchema, ScriptLineSchema
from utils.web.base_controller import BaseAPIController
from utils.web.web_decorators import requires_show, no_live_session
from utils.web.route import ApiRoute, ApiVersion


@ApiRoute('show/script/config', ApiVersion.V1)
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


@ApiRoute('show/script/revisions', ApiVersion.V1)
class ScriptRevisionsController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']
        revisions_schema = ScriptRevisionsSchema()

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

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                data = escape.json_decode(self.request.body)

                script: Script = session.query(Script).filter(Script.show_id == show.id).first()
                if not script:
                    self.set_status(404)
                    await self.finish({'message': '404 script not found'})
                    return
                self.requires_role(script, Role.WRITE)

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
                for cue_association in current_rev.cue_associations:
                    new_rev.cue_associations.append(CueAssociation(
                        revision_id=new_rev.id,
                        line_id=cue_association.line_id,
                        cue_id=cue_association.cue_id
                    ))

                script.current_revision = new_rev.id
                session.commit()

                self.set_status(200)
                await self.finish({'message': 'Successfully added script revision'})
                await self.application.ws_send_to_all('NOOP', 'GET_SCRIPT_REVISIONS', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show: Show = session.query(Show).get(show_id)
            if show:
                data = escape.json_decode(self.request.body)

                script: Script = session.query(Script).filter(Script.show_id == show.id).first()
                if not script:
                    self.set_status(404)
                    await self.finish({'message': '404 script not found'})
                    return
                self.requires_role(script, Role.WRITE)

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

                changed_rev = False
                if script.current_revision == rev.id:
                    changed_rev = True
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
                if changed_rev:
                    await self.application.ws_send_to_all('NOOP', 'SCRIPT_REVISION_CHANGED', {})
                else:
                    await self.application.ws_send_to_all('NOOP', 'GET_SCRIPT_REVISIONS', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})


@ApiRoute('show/script/revisions/current', ApiVersion.V1)
class ScriptCurrentRevisionController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

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

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                self.requires_role(show, Role.WRITE)
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
                await self.application.ws_send_to_all('NOOP', 'SCRIPT_REVISION_CHANGED', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})


@ApiRoute('/show/script', ApiVersion.V1)
class ScriptController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        page = self.get_query_argument('page', None)
        if not page:
            self.set_status(400)
            self.finish({'message': 'Page not given'})
            return

        page = int(page)

        line_schema = ScriptLineSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                script: Script = session.query(Script).filter(Script.show_id == show.id).first()

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision)
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
                    if (page == 1 and line.previous_line is None
                            or line.previous_line.page == page - 1):
                        if first_line:
                            self.set_status(400)
                            self.finish({'message': 'Failed to establish page line order'})
                            return

                        first_line = line

                lines = []
                line_revision = first_line
                while line_revision:
                    if line_revision.line.page != page:
                        break

                    lines.append(line_schema.dump(line_revision.line))
                    line_revision = session.query(ScriptLineRevisionAssociation).get(
                        {'revision_id': revision.id, 'line_id': line_revision.next_line_id})

                self.set_status(200)
                self.finish({'lines': lines, 'page': page})
            else:
                self.set_status(404)
                self.finish({'message': '404 show not found'})
                return

    @staticmethod
    def _validate_line(line_json):
        if line_json['stage_direction']:
            if len(line_json['line_parts']) > 1:
                return False, 'Stage directions can only have 1 line part'
            line_part = line_json['line_parts'][0]
            if line_part['character_id'] is not None:
                return False, 'Stage directions cannot have characters'
            if line_part['character_group_id'] is not None:
                return False, 'Stage directions cannot have character groups'
            if line_part['line_text'] is None:
                return False, 'Stage directions must contain text'
        else:
            for line_part in line_json['line_parts']:
                if line_part['line_text'] is None:
                    return False, 'Line parts must contain text'
                if line_part['character_id'] is None and line_part['character_group_id'] is None:
                    return False, 'Line parts must contain a character or character group'
                if line_part['character_id'] and line_part['character_group_id']:
                    return False, 'Line parts cannot contain both a character and character group'

        return True, ''

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        page = self.get_query_argument('page', None)
        if not page:
            self.set_status(400)
            await self.finish({'message': 'Page not given'})
            return

        page = int(page)

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                script: Script = session.query(Script).filter(Script.show_id == show.id).first()
                self.requires_role(script, Role.WRITE)

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision)
                else:
                    self.set_status(400)
                    await self.finish({'message': 'Script does not have a current revision'})
                    return

                lines = escape.json_decode(self.request.body)

                previous_line: Optional[ScriptLineRevisionAssociation] = None
                for index, line in enumerate(lines):

                    # Validate each line before we do anything with it
                    valid_status, valid_reason = self._validate_line(line)
                    if not valid_status:
                        self.set_status(400)
                        await self.finish({'message': valid_reason})
                        return

                    # Create the initial line object, and flush it to the database as we need
                    # the ID for further in the loop
                    line_obj = ScriptLine(act_id=line['act_id'],
                                          scene_id=line['scene_id'],
                                          page=line['page'],
                                          stage_direction=line['stage_direction'])
                    session.add(line_obj)
                    session.flush()

                    # Line revision object to keep track of that thing
                    line_revision = ScriptLineRevisionAssociation(revision_id=revision.id,
                                                                  line_id=line_obj.id)
                    session.add(line_revision)
                    session.flush()

                    if index == 0 and page > 1:
                        # First line and not the first page, so need to get the last line of the
                        # previous page and set its next line to this one
                        prev_page_lines: List[ScriptLineRevisionAssociation] = session.query(
                            ScriptLineRevisionAssociation).filter(
                            ScriptLineRevisionAssociation.revision_id == revision.id,
                            ScriptLineRevisionAssociation.line.has(page=page - 1)).all()

                        if not prev_page_lines:
                            self.set_status(400)
                            await self.finish({
                                'message': 'Previous page does not contain any lines'
                            })
                            return

                        # Perform some iteration here to establish the first line of the script
                        # of the previous page
                        first_line = None
                        for prev_line in prev_page_lines:
                            if (prev_line.previous_line is None or
                                    prev_line.previous_line.page == prev_line.line.page - 1):
                                if first_line:
                                    self.set_status(400)
                                    await self.finish({
                                        'message': 'Failed to establish page line order for '
                                                   'previous page'
                                    })
                                    return

                                first_line = prev_line

                        # Construct an ordered list of lines, because we need to get the last
                        # line of a page, and right now there is no better way of doing it
                        previous_lines = []
                        prev_line = first_line
                        while prev_line:
                            if prev_line.line.page != page - 1:
                                break

                            previous_lines.append(prev_line)
                            prev_line = session.query(ScriptLineRevisionAssociation).get({
                                'revision_id': revision.id,
                                'line_id': prev_line.next_line_id
                            })

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
                                                  character_group_id=line_part[
                                                      'character_group_id'],
                                                  line_text=line_part['line_text'])
                        session.add(part_obj)
                        line_obj.line_parts.append(part_obj)

                    # Flush once more at the end of the loop iteration (not for luck,
                    # I promise...!) to ensure the database is up-to-date for the next time
                    # around
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

    @staticmethod
    def _create_new_line(session, revision, line, previous_line, with_association=True):
        # Create the line object
        line_obj = ScriptLine(act_id=line['act_id'],
                              scene_id=line['scene_id'],
                              page=line['page'],
                              stage_direction=line['stage_direction'])
        session.add(line_obj)
        session.flush()

        line_association = None
        if with_association:
            # Line revision object to keep track of that thing
            line_association = ScriptLineRevisionAssociation(revision_id=revision.id,
                                                             line_id=line_obj.id)
            session.add(line_association)
            session.flush()

            # Set the next and previous line reference
            if previous_line:
                previous_line.next_line = line_obj
                line_association.previous_line = previous_line.line
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

        # Flush the DB to add the line parts
        session.flush()

        return line_association, line_obj

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        page = self.get_query_argument('page', None)
        if not page:
            self.set_status(400)
            await self.finish({'message': 'Page not given'})
            return

        page = int(page)

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                script: Script = session.query(Script).filter(Script.show_id == show.id).first()
                self.requires_role(script, Role.WRITE)

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision)
                else:
                    self.set_status(400)
                    await self.finish({'message': 'Script does not have a current revision'})
                    return

                request_body = escape.json_decode(self.request.body)

                lines = request_body.get('page', None)
                if lines is None:
                    self.set_status(400)
                    await self.finish({
                        'message': 'Malformed request body, could not find `page` data'
                    })
                    return

                status = request_body.get('status', None)
                if status is None:
                    self.set_status(400)
                    await self.finish({
                        'message': 'Malformed request body, could not find `status` data'
                    })
                    return

                previous_line: Optional[ScriptLineRevisionAssociation] = None
                for index, line in enumerate(lines):
                    if index in status['added']:
                        # Validate the line
                        valid_status, valid_reason = self._validate_line(line)
                        if not valid_status:
                            self.set_status(400)
                            await self.finish({'message': valid_reason})
                            return

                        line_association, line_object = self._create_new_line(
                            session, revision, line, previous_line)
                        previous_line = line_association
                    elif index in status['deleted']:
                        curr_association: ScriptLineRevisionAssociation = session.query(
                            ScriptLineRevisionAssociation).get(
                            {'revision_id': revision.id, 'line_id': line['id']})

                        # Logic for handling next/previous line associations
                        if curr_association.next_line and curr_association.previous_line:
                            # Next line and previous line, so need to update both
                            next_association: ScriptLineRevisionAssociation = session.query(
                                ScriptLineRevisionAssociation).get(
                                {'revision_id': revision.id,
                                 'line_id': curr_association.next_line.id})
                            next_association.previous_line = curr_association.previous_line
                            session.flush()

                            prev_association: ScriptLineRevisionAssociation = session.query(
                                ScriptLineRevisionAssociation).get(
                                {'revision_id': revision.id,
                                 'line_id': curr_association.previous_line.id})
                            prev_association.next_line = next_association.line
                            session.flush()
                        elif curr_association.next_line:
                            # No previous line, so need to update next line only
                            next_association: ScriptLineRevisionAssociation = session.query(
                                ScriptLineRevisionAssociation).get(
                                {'revision_id': revision.id,
                                 'line_id': curr_association.next_line.id})
                            next_association.previous_line = None
                            session.flush()
                        elif curr_association.previous_line:
                            # No next line, so need to update previous line only
                            prev_association: ScriptLineRevisionAssociation = session.query(
                                ScriptLineRevisionAssociation).get(
                                {'revision_id': revision.id,
                                 'line_id': curr_association.previous_line.id})
                            prev_association.next_line = None
                            session.flush()
                        session.delete(curr_association)
                    elif index in status['updated']:
                        # Validate the line
                        valid_status, valid_reason = self._validate_line(line)
                        if not valid_status:
                            self.set_status(400)
                            await self.finish({'message': valid_reason})
                            return

                        curr_association: ScriptLineRevisionAssociation = session.query(
                            ScriptLineRevisionAssociation).get(
                            {'revision_id': revision.id, 'line_id': line['id']})
                        curr_line = curr_association.line

                        if not curr_association:
                            self.set_status(500)
                            await self.finish({'message': 'Unable to load line data'})
                            return

                        line_association, line_object = self._create_new_line(
                            session, revision, line, previous_line, with_association=False)
                        curr_association.line = line_object
                        if previous_line:
                            previous_line.next_line = line_object
                            curr_association.previous_line = previous_line.line
                        session.flush()

                        if len(curr_line.revision_associations) == 0:
                            session.delete(curr_line)

                        session.flush()

                        previous_line = curr_association
                    else:
                        previous_line = session.query(ScriptLineRevisionAssociation).get(
                            {'revision_id': revision.id, 'line_id': line['id']})

            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})
                return


@ApiRoute('/show/script/max_page', ApiVersion.V1)
class ScriptMaxPageController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                script: Script = session.query(Script).filter(Script.show_id == show.id).first()

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision)
                else:
                    self.set_status(400)
                    self.finish({'message': 'Script does not have a current revision'})
                    return

                line_ids = session.query(ScriptLineRevisionAssociation).with_entities(
                    ScriptLineRevisionAssociation.line_id).filter(
                    ScriptLineRevisionAssociation.revision_id == revision.id)
                max_page = session.query(ScriptLine).with_entities(
                    func.max(ScriptLine.page)).where(
                    ScriptLine.id.in_(line_ids)).first()[0]

                if max_page is None:
                    max_page = 0

                self.set_status(200)
                self.finish({
                    'max_page': max_page
                })
            else:
                self.set_status(404)
                self.finish({'message': '404 show not found'})
                return
