import collections
from typing import List

from tornado import escape

from models.cue import CueType, CueAssociation, Cue
from models.script import ScriptRevision, Script
from models.show import Show
from schemas.schemas import CueTypeSchema, CueSchema
from utils.web.base_controller import BaseAPIController
from utils.web.web_decorators import requires_show, no_live_session
from utils.web.route import ApiRoute, ApiVersion


@ApiRoute('show/cues/types', ApiVersion.v1)
class CueTypesController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']
        cue_type_schema = CueTypeSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                cue_types = [cue_type_schema.dump(c) for c in show.cue_type_list]
                self.set_status(200)
                self.finish({'cue_types': cue_types})
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

                prefix: str = data.get('prefix', None)
                if not prefix:
                    self.set_status(400)
                    await self.finish({'message': 'Prefix missing'})
                    return

                description: str = data.get('description', None)

                colour: str = data.get('colour', None)
                if not colour:
                    self.set_status(400)
                    await self.finish({'message': 'Colour missing'})
                    return

                session.add(CueType(
                    show_id=show_id,
                    prefix=prefix,
                    description=description,
                    colour=colour))
                session.commit()

                self.set_status(200)
                await self.finish({'message': 'Successfully added cue type'})

                await self.application.ws_send_to_all('NOOP', 'GET_CUE_TYPES', {})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show['id']

        with self.make_session() as session:
            show: Show = session.query(Show).get(show_id)
            if show:
                data = escape.json_decode(self.request.body)

                cue_type_id = data.get('id', None)
                if not cue_type_id:
                    self.set_status(400)
                    await self.finish({'message': 'ID missing'})
                    return

                cue_type: CueType = session.query(CueType).get(cue_type_id)
                if not cue_type:
                    self.set_status(404)
                    await self.finish({'message': '404 cue type not found'})
                    return

                prefix: str = data.get('prefix', None)
                if not prefix:
                    self.set_status(400)
                    await self.finish({'message': 'Prefix missing'})
                    return

                description: str = data.get('description', None)

                colour: str = data.get('colour', None)
                if not colour:
                    self.set_status(400)
                    await self.finish({'message': 'Colour missing'})
                    return

                cue_type.prefix = prefix
                cue_type.description = description
                cue_type.colour = colour
                session.commit()

                self.set_status(200)
                await self.finish({'message': 'Successfully added cue type'})

                await self.application.ws_send_to_all('NOOP', 'GET_CUE_TYPES', {})
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

                cue_type_id = data.get('id', None)
                if not cue_type_id:
                    self.set_status(400)
                    await self.finish({'message': 'ID missing'})
                    return

                entry: CueType = session.get(CueType, cue_type_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully deleted cue type'})

                    await self.application.ws_send_to_all('NOOP', 'GET_CUE_TYPES', {})
                else:
                    self.set_status(404)
                    await self.finish({'message': '404 cue type not found'})
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})


@ApiRoute('show/cues', ApiVersion.v1)
class CueController(BaseAPIController):

    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show['id']
        cue_schema = CueSchema()

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

                revision_cues: List[CueAssociation] = session.query(
                    CueAssociation).filter(CueAssociation.revision_id == revision.id).all()

                cues = collections.defaultdict(list)
                for association in revision_cues:
                    cues[association.line_id].append(cue_schema.dump(association.cue))

                self.set_status(200)
                self.finish({'cues': cues})
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
                script: Script = session.query(Script).filter(Script.show_id == show.id).first()

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision)
                else:
                    self.set_status(400)
                    await self.finish({'message': 'Script does not have a current revision'})
                    return

                data = escape.json_decode(self.request.body)

                cue_type_id: int = data.get('cueType', None)
                if not cue_type_id:
                    self.set_status(400)
                    await self.finish({'message': 'Cue Type missing'})
                    return

                ident: str = data.get('ident', None)
                if not ident:
                    self.set_status(400)
                    await self.finish({'message': 'Identifier missing'})
                    return

                line_id: int = data.get('lineId', None)
                if not line_id:
                    self.set_status(400)
                    await self.finish({'message': 'Line ID missing'})
                    return

                cue = Cue(cue_type_id=cue_type_id, ident=ident)
                session.add(cue)
                session.flush()

                session.add(CueAssociation(revision_id=revision.id, line_id=line_id,
                                           cue_id=cue.id))
                session.commit()

                self.set_status(200)
                await self.finish({'message': 'Successfully added cue'})

                await self.application.ws_send_to_all('NOOP', 'LOAD_CUES', {})

            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def patch(self):
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
                    await self.finish({'message': 'Script does not have a current revision'})
                    return

                data = escape.json_decode(self.request.body)

                cue_id: int = data.get('cueId')
                if not cue_id:
                    self.set_status(400)
                    await self.finish({'message': 'Cue ID missing'})
                    return

                cue_type_id: int = data.get('cueType', None)
                if not cue_type_id:
                    self.set_status(400)
                    await self.finish({'message': 'Cue Type missing'})
                    return

                cue_type = session.query(CueType).get(cue_type_id)
                if not cue_type:
                    self.set_status(400)
                    await self.finish({'message': 'Cue Type is not valid, or cannot be found'})
                    return

                ident: str = data.get('ident', None)
                if not ident:
                    self.set_status(400)
                    await self.finish({'message': 'Identifier missing'})
                    return

                line_id: int = data.get('lineId', None)
                if not line_id:
                    self.set_status(400)
                    await self.finish({'message': 'Line ID missing'})
                    return

                cue: Cue = session.query(Cue).get(cue_id)
                if not cue:
                    self.set_status(404)
                    await self.finish({'message': '404 cue not found'})
                    return

                current_association: CueAssociation = session.query(CueAssociation).get(
                    {'revision_id': revision.id, 'line_id': line_id, 'cue_id': cue_id})

                if not current_association:
                    self.set_status(400)
                    await self.finish({'message': 'Unable to load cue line data'})
                    return

                if len(cue.revision_associations) == 1:
                    if cue.revision_associations[0] == current_association:
                        cue.cue_type = cue_type
                        cue.ident = ident
                    else:
                        self.set_status(400)
                        await self.finish({'message': 'Cannot edit cue for a revision that is '
                                                      'not loaded'})
                        return
                else:
                    new_cue = Cue(ident=ident, cue_type_id=cue_type_id)
                    session.add(new_cue)
                    session.flush()

                    current_association.cue = new_cue

                session.commit()
                self.set_status(200)
                await self.finish({'message': 'Successfully edited cue'})
                await self.application.ws_send_to_all('NOOP', 'LOAD_CUES', {})

            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})

    @requires_show
    @no_live_session
    async def delete(self):
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
                    await self.finish({'message': 'Script does not have a current revision'})
                    return

                data = escape.json_decode(self.request.body)

                cue_id: int = data.get('cueId')
                if not cue_id:
                    self.set_status(400)
                    await self.finish({'message': 'Cue ID missing'})
                    return

                line_id: int = data.get('lineId')
                if not line_id:
                    self.set_status(400)
                    await self.finish({'message': 'Line ID missing'})
                    return

                association_object = session.query(CueAssociation).get(
                    {'revision_id': revision.id, 'line_id': line_id, 'cue_id': cue_id})

                if association_object:
                    session.delete(association_object)
                    session.commit()

                    self.set_status(200)
                    await self.finish({'message': 'Successfully deleted cue'})
                    await self.application.ws_send_to_all('NOOP', 'LOAD_CUES', {})
                else:
                    self.set_status(400)
                    await self.finish({'message': 'Could not find cue association object'})
                    return
            else:
                self.set_status(404)
                await self.finish({'message': '404 show not found'})
