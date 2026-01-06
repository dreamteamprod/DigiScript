import collections
import difflib
from typing import List

from sqlalchemy import func, select
from tornado import escape

from models.cue import Cue, CueAssociation, CueType
from models.script import Script, ScriptLine, ScriptLineType, ScriptRevision
from models.show import Show
from rbac.role import Role
from schemas.schemas import CueSchema, CueTypeSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/cues/types", ApiVersion.V1)
class CueTypesController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        cue_type_schema = CueTypeSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                cue_types = [cue_type_schema.dump(c) for c in show.cue_type_list]
                self.set_status(200)
                self.finish({"cue_types": cue_types})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                prefix: str = data.get("prefix", None)
                if not prefix:
                    self.set_status(400)
                    await self.finish({"message": "Prefix missing"})
                    return

                description: str = data.get("description", None)

                colour: str = data.get("colour", None)
                if not colour:
                    self.set_status(400)
                    await self.finish({"message": "Colour missing"})
                    return

                new_cuetype = CueType(
                    show_id=show_id,
                    prefix=prefix,
                    description=description,
                    colour=colour,
                )
                session.add(new_cuetype)
                session.commit()

                self.set_status(200)
                await self.finish(
                    {"id": new_cuetype.id, "message": "Successfully added cue type"}
                )

                await self.application.ws_send_to_all("NOOP", "GET_CUE_TYPES", {})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)
                data = escape.json_decode(self.request.body)

                cue_type_id = data.get("id", None)
                if not cue_type_id:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                cue_type: CueType = session.get(CueType, cue_type_id)
                if not cue_type:
                    self.set_status(404)
                    await self.finish({"message": "404 cue type not found"})
                    return

                prefix: str = data.get("prefix", None)
                if not prefix:
                    self.set_status(400)
                    await self.finish({"message": "Prefix missing"})
                    return

                description: str = data.get("description", None)

                colour: str = data.get("colour", None)
                if not colour:
                    self.set_status(400)
                    await self.finish({"message": "Colour missing"})
                    return

                cue_type.prefix = prefix
                cue_type.description = description
                cue_type.colour = colour
                session.commit()

                self.set_status(200)
                await self.finish({"message": "Successfully added cue type"})

                await self.application.ws_send_to_all("NOOP", "GET_CUE_TYPES", {})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                self.requires_role(show, Role.WRITE)

                cue_type_id_str = self.get_argument("id", None)
                if not cue_type_id_str:
                    self.set_status(400)
                    await self.finish({"message": "ID missing"})
                    return

                try:
                    cue_type_id = int(cue_type_id_str)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": "Invalid ID"})
                    return

                entry: CueType = session.get(CueType, cue_type_id)
                if entry:
                    session.delete(entry)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted cue type"})

                    await self.application.ws_send_to_all("NOOP", "GET_CUE_TYPES", {})
                else:
                    self.set_status(404)
                    await self.finish({"message": "404 cue type not found"})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


@ApiRoute("show/cues", ApiVersion.V1)
class CueController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        cue_schema = CueSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()

                if script.current_revision:
                    revision: ScriptRevision = session.get(
                        ScriptRevision, script.current_revision
                    )
                else:
                    self.set_status(400)
                    self.finish({"message": "Script does not have a current revision"})
                    return

                revision_cues: List[CueAssociation] = session.scalars(
                    select(CueAssociation).where(
                        CueAssociation.revision_id == revision.id
                    )
                ).all()

                cues = collections.defaultdict(list)
                for association in revision_cues:
                    cues[association.line_id].append(cue_schema.dump(association.cue))

                self.set_status(200)
                self.finish({"cues": cues})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})

    @requires_show
    async def post(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()

                if script.current_revision:
                    revision: ScriptRevision = session.get(
                        ScriptRevision, script.current_revision
                    )
                else:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Script does not have a current revision"}
                    )
                    return

                data = escape.json_decode(self.request.body)

                cue_type_id: int = data.get("cueType", None)
                if not cue_type_id:
                    self.set_status(400)
                    await self.finish({"message": "Cue Type missing"})
                    return

                cue_type = session.get(CueType, cue_type_id)
                if not cue_type:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Cue Type is not valid, or cannot be found"}
                    )
                    return
                self.requires_role(cue_type, Role.WRITE)

                ident: str = data.get("ident", None)
                if not ident:
                    self.set_status(400)
                    await self.finish({"message": "Identifier missing"})
                    return

                line_id: int = data.get("lineId", None)
                if not line_id:
                    self.set_status(400)
                    await self.finish({"message": "Line ID missing"})
                    return

                line: ScriptLine = session.get(ScriptLine, line_id)
                if not line:
                    self.set_status(400)
                    await self.finish({"message": "Line ID is not valid"})
                    return
                if line.line_type == ScriptLineType.SPACING:
                    self.set_status(400)
                    await self.finish({"message": "Cannot add cues to spacing lines"})
                    return

                cue = Cue(cue_type_id=cue_type_id, ident=ident)
                session.add(cue)
                session.flush()

                session.add(
                    CueAssociation(
                        revision_id=revision.id, line_id=line_id, cue_id=cue.id
                    )
                )
                session.commit()

                self.set_status(200)
                await self.finish({"message": "Successfully added cue"})

                await self.application.ws_send_to_all("NOOP", "LOAD_CUES", {})

            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def patch(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()

                if script.current_revision:
                    revision: ScriptRevision = session.get(
                        ScriptRevision, script.current_revision
                    )
                else:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Script does not have a current revision"}
                    )
                    return

                data = escape.json_decode(self.request.body)

                cue_id: int = data.get("cueId")
                if not cue_id:
                    self.set_status(400)
                    await self.finish({"message": "Cue ID missing"})
                    return

                cue_type_id: int = data.get("cueType", None)
                if not cue_type_id:
                    self.set_status(400)
                    await self.finish({"message": "Cue Type missing"})
                    return

                cue_type = session.get(CueType, cue_type_id)
                if not cue_type:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Cue Type is not valid, or cannot be found"}
                    )
                    return
                self.requires_role(cue_type, Role.WRITE)

                ident: str = data.get("ident", None)
                if not ident:
                    self.set_status(400)
                    await self.finish({"message": "Identifier missing"})
                    return

                line_id: int = data.get("lineId", None)
                if not line_id:
                    self.set_status(400)
                    await self.finish({"message": "Line ID missing"})
                    return

                cue: Cue = session.get(Cue, cue_id)
                if not cue:
                    self.set_status(404)
                    await self.finish({"message": "404 cue not found"})
                    return

                current_association: CueAssociation = session.get(
                    CueAssociation,
                    {"revision_id": revision.id, "line_id": line_id, "cue_id": cue_id},
                )

                if not current_association:
                    self.set_status(400)
                    await self.finish({"message": "Unable to load cue line data"})
                    return

                if len(cue.revision_associations) == 1:
                    if cue.revision_associations[0] == current_association:
                        cue.cue_type = cue_type
                        cue.ident = ident
                    else:
                        self.set_status(400)
                        await self.finish(
                            {
                                "message": "Cannot edit cue for a revision that is "
                                "not loaded"
                            }
                        )
                        return
                else:
                    new_cue = Cue(ident=ident, cue_type_id=cue_type_id)
                    session.add(new_cue)
                    session.flush()

                    current_association.cue = new_cue

                session.commit()
                self.set_status(200)
                await self.finish({"message": "Successfully edited cue"})
                await self.application.ws_send_to_all("NOOP", "LOAD_CUES", {})

            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})

    @requires_show
    @no_live_session
    async def delete(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if show:
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()

                if script.current_revision:
                    revision: ScriptRevision = session.get(
                        ScriptRevision, script.current_revision
                    )
                else:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Script does not have a current revision"}
                    )
                    return

                cue_id_str = self.get_argument("cueId", None)
                if not cue_id_str:
                    self.set_status(400)
                    await self.finish({"message": "Cue ID missing"})
                    return

                try:
                    cue_id = int(cue_id_str)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": "Invalid Cue ID"})
                    return

                cue = session.get(Cue, cue_id)
                cue_type = session.get(CueType, cue.cue_type_id)
                self.requires_role(cue_type, Role.WRITE)

                line_id_str = self.get_argument("lineId", None)
                if not line_id_str:
                    self.set_status(400)
                    await self.finish({"message": "Line ID missing"})
                    return

                try:
                    line_id = int(line_id_str)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": "Invalid Line ID"})
                    return

                association_object = session.get(
                    CueAssociation,
                    {"revision_id": revision.id, "line_id": line_id, "cue_id": cue_id},
                )

                if association_object:
                    session.delete(association_object)
                    session.commit()

                    self.set_status(200)
                    await self.finish({"message": "Successfully deleted cue"})
                    await self.application.ws_send_to_all("NOOP", "LOAD_CUES", {})
                else:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Could not find cue association object"}
                    )
                    return
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


@ApiRoute("show/cues/stats", ApiVersion.V1)
class CueStatsController(BaseAPIController):
    async def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if show:
                script: Script = session.scalars(
                    select(Script).where(Script.show_id == show.id)
                ).first()

                if script.current_revision:
                    revision: ScriptRevision = session.get(
                        ScriptRevision, script.current_revision
                    )
                else:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Script does not have a current revision"}
                    )
                    return

                cue_counts = collections.defaultdict(
                    lambda: collections.defaultdict(
                        lambda: collections.defaultdict(int)
                    )
                )
                for cue_association in revision.cue_associations:
                    line: ScriptLine = cue_association.line
                    cue = session.get(Cue, cue_association.cue_id)
                    if line is not None and cue is not None:
                        cue_counts[cue.cue_type_id][line.act_id][line.scene_id] += 1

                self.set_status(200)
                await self.finish({"cue_counts": cue_counts})
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})


@ApiRoute("show/cues/search", ApiVersion.V1)
class CueSearchController(BaseAPIController):
    @requires_show
    async def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        # Extract query parameters
        identifier = self.get_query_argument("identifier", None)
        if not identifier or identifier.strip() == "":
            self.set_status(400)
            await self.finish({"message": "Identifier parameter is required"})
            return
        identifier = identifier.strip()

        cue_type_id = self.get_query_argument("cue_type_id", None)
        if not cue_type_id:
            self.set_status(400)
            await self.finish({"message": "Cue type ID parameter is required"})
            return

        try:
            cue_type_id = int(cue_type_id)
        except ValueError:
            self.set_status(400)
            await self.finish({"message": "Invalid cue_type_id parameter"})
            return

        with self.make_session() as session:
            show: Show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
                return

            script: Script = session.scalars(
                select(Script).where(Script.show_id == show.id)
            ).first()

            if not script or not script.current_revision:
                self.set_status(400)
                await self.finish(
                    {"message": "Script does not have a current revision"}
                )
                return

            revision: ScriptRevision = session.get(
                ScriptRevision, script.current_revision
            )

            # Query for exact matches (case-insensitive)
            exact_match_stmt = (
                select(CueAssociation, Cue, CueType, ScriptLine)
                .join(CueAssociation.cue)
                .join(CueAssociation.line)
                .join(Cue.cue_type)
                .where(
                    CueAssociation.revision_id == revision.id,
                    Cue.cue_type_id == cue_type_id,
                    func.lower(Cue.ident) == identifier.lower(),
                )
            )
            exact_results = session.execute(exact_match_stmt).all()

            cue_schema = CueSchema()
            cue_type_schema = CueTypeSchema()

            # If exact matches found, return them
            if exact_results:
                exact_matches = []
                for cue_assoc, cue, cue_type, line in exact_results:
                    exact_matches.append(
                        {
                            "cue": cue_schema.dump(cue),
                            "cue_type": cue_type_schema.dump(cue_type),
                            "location": {
                                "page": line.page,
                                "line_id": line.id,
                                "act_id": line.act_id,
                                "scene_id": line.scene_id,
                            },
                        }
                    )
                self.set_status(200)
                await self.finish(
                    {
                        "exact_matches": exact_matches,
                        "suggestions": [],
                    }
                )
                return

            # No exact matches - calculate fuzzy matches
            # Query all cues of this type in the current revision
            all_cues_stmt = (
                select(CueAssociation, Cue, CueType, ScriptLine)
                .join(CueAssociation.cue)
                .join(CueAssociation.line)
                .join(Cue.cue_type)
                .where(
                    CueAssociation.revision_id == revision.id,
                    Cue.cue_type_id == cue_type_id,
                )
            )

            all_cues = session.execute(all_cues_stmt).all()

            # Calculate similarity scores
            suggestions_with_scores = []
            search_lower = identifier.lower()

            for cue_assoc, cue, cue_type, line in all_cues:
                if cue.ident:
                    ratio = difflib.SequenceMatcher(
                        None, search_lower, cue.ident.lower()
                    ).ratio()

                    if ratio > 0.3:  # Minimum similarity threshold
                        suggestions_with_scores.append(
                            {
                                "cue": cue_schema.dump(cue),
                                "cue_type": cue_type_schema.dump(cue_type),
                                "location": {
                                    "page": line.page,
                                    "line_id": line.id,
                                    "act_id": line.act_id,
                                    "scene_id": line.scene_id,
                                },
                                "similarity_score": ratio,
                            }
                        )

            # Sort by score descending, take top 5
            suggestions_with_scores.sort(
                key=lambda x: x["similarity_score"], reverse=True
            )
            suggestions = suggestions_with_scores[:5]

            self.set_status(200)
            await self.finish(
                {
                    "exact_matches": [],
                    "suggestions": suggestions,
                }
            )
