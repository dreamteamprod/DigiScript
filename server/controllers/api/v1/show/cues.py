import collections
import difflib
from typing import List

from sqlalchemy import func, select
from tornado import escape

from controllers.api.constants import (
    ERROR_COLOUR_MISSING,
    ERROR_CUE_GROUP_EMPTY,
    ERROR_CUE_GROUP_ID_MISSING,
    ERROR_CUE_GROUP_NOT_FOUND,
    ERROR_CUE_ID_MISSING,
    ERROR_CUE_NOT_FOUND,
    ERROR_CUE_TYPE_MISSING,
    ERROR_CUE_TYPE_NOT_FOUND,
    ERROR_ID_MISSING,
    ERROR_IDENTIFIER_MISSING,
    ERROR_INVALID_ID,
    ERROR_LINE_ID_MISSING,
    ERROR_PREFIX_MISSING,
    ERROR_SHOW_NOT_FOUND,
)
from models.cue import Cue, CueAssociation, CueGroup, CueType
from models.script import Script, ScriptLine, ScriptLineType, ScriptRevision
from models.show import Show
from models.user import User
from rbac.role import Role
from schemas.schemas import CueGroupSchema, CueSchema, CueTypeSchema
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
                self.finish({"message": ERROR_SHOW_NOT_FOUND})

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
                    await self.finish({"message": ERROR_PREFIX_MISSING})
                    return

                description: str = data.get("description", None)

                colour: str = data.get("colour", None)
                if not colour:
                    self.set_status(400)
                    await self.finish({"message": ERROR_COLOUR_MISSING})
                    return

                new_cuetype = CueType(
                    show_id=show_id,
                    prefix=prefix,
                    description=description,
                    colour=colour,
                )
                session.add(new_cuetype)
                session.commit()

                user = session.get(User, self.current_user["id"])
                self.application.rbac.give_role(
                    user, new_cuetype, Role.READ | Role.WRITE | Role.EXECUTE
                )
                for socket in self.application.get_all_ws(user.id):
                    await socket.write_message(
                        {"OP": "NOOP", "DATA": {}, "ACTION": "GET_CURRENT_RBAC"}
                    )

                self.set_status(200)
                await self.finish(
                    {"id": new_cuetype.id, "message": "Successfully added cue type"}
                )

                await self.application.ws_send_to_all("NOOP", "GET_CUE_TYPES", {})
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

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
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                cue_type: CueType = session.get(CueType, cue_type_id)
                if not cue_type:
                    self.set_status(404)
                    await self.finish({"message": ERROR_CUE_TYPE_NOT_FOUND})
                    return

                prefix: str = data.get("prefix", None)
                if not prefix:
                    self.set_status(400)
                    await self.finish({"message": ERROR_PREFIX_MISSING})
                    return

                description: str = data.get("description", None)

                colour: str = data.get("colour", None)
                if not colour:
                    self.set_status(400)
                    await self.finish({"message": ERROR_COLOUR_MISSING})
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
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

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
                    await self.finish({"message": ERROR_ID_MISSING})
                    return

                try:
                    cue_type_id = int(cue_type_id_str)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": ERROR_INVALID_ID})
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
                    await self.finish({"message": ERROR_CUE_TYPE_NOT_FOUND})
            else:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})


@ApiRoute("show/cues/types/import", ApiVersion.V1)
class CueTypesImportController(BaseAPIController):
    @requires_show
    def get(self):
        """
        Return all cue types from all other shows, grouped by show.

        :returns: JSON with a ``cue_type_groups`` key containing a list of show
            objects, each with ``id``, ``name``, and ``cue_types`` fields.
        """
        current_show_id = self.get_current_show()["id"]
        schema = CueTypeSchema()

        with self.make_session() as session:
            rows = session.execute(
                select(Show, CueType)
                .join(CueType, CueType.show_id == Show.id)
                .where(Show.id != current_show_id)
                .order_by(Show.id)
            ).all()

            shows_map: dict = {}
            for show, cue_type in rows:
                if show.id not in shows_map:
                    shows_map[show.id] = {
                        "id": show.id,
                        "name": show.name,
                        "cue_types": [],
                    }
                shows_map[show.id]["cue_types"].append(schema.dump(cue_type))

        self.set_status(200)
        self.finish({"cue_type_groups": list(shows_map.values())})


@ApiRoute("show/cues", ApiVersion.V1)
class CueController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]
        cue_schema = CueSchema()
        group_schema = CueGroupSchema()

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
                groups_seen: dict = {}
                for association in revision_cues:
                    cue_data = cue_schema.dump(association.cue)
                    cue_data["group_id"] = association.group_id
                    cue_data["sort_order"] = association.sort_order
                    cues[association.line_id].append(cue_data)
                    if association.group_id and association.group_id not in groups_seen:
                        groups_seen[association.group_id] = association.group

                cue_groups = [group_schema.dump(g) for g in groups_seen.values()]

                self.set_status(200)
                self.finish({"cues": cues, "cue_groups": cue_groups})
            else:
                self.set_status(404)
                self.finish({"message": ERROR_SHOW_NOT_FOUND})

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
                    await self.finish({"message": ERROR_CUE_TYPE_MISSING})
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
                    await self.finish({"message": ERROR_IDENTIFIER_MISSING})
                    return

                line_id: int = data.get("lineId", None)
                if not line_id:
                    self.set_status(400)
                    await self.finish({"message": ERROR_LINE_ID_MISSING})
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
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

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
                    await self.finish({"message": ERROR_CUE_ID_MISSING})
                    return

                cue_type_id: int = data.get("cueType", None)
                if not cue_type_id:
                    self.set_status(400)
                    await self.finish({"message": ERROR_CUE_TYPE_MISSING})
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
                    await self.finish({"message": ERROR_IDENTIFIER_MISSING})
                    return

                line_id: int = data.get("lineId", None)
                if not line_id:
                    self.set_status(400)
                    await self.finish({"message": ERROR_LINE_ID_MISSING})
                    return

                cue: Cue = session.get(Cue, cue_id)
                if not cue:
                    self.set_status(404)
                    await self.finish({"message": ERROR_CUE_NOT_FOUND})
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
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})

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
                    await self.finish({"message": ERROR_CUE_ID_MISSING})
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
                    await self.finish({"message": ERROR_LINE_ID_MISSING})
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
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})


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
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})


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
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
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


@ApiRoute("show/cues/groups", ApiVersion.V1)
class CueGroupController(BaseAPIController):
    def _get_revision(self, session, show_id):
        """Return (script, revision) or (None, None) if unavailable."""
        show = session.get(Show, show_id)
        if not show:
            return None, None
        script: Script = session.scalars(
            select(Script).where(Script.show_id == show.id)
        ).first()
        if not script or not script.current_revision:
            return script, None
        return script, session.get(ScriptRevision, script.current_revision)

    @requires_show
    async def post(self):
        """Create a new cue group and add its member cues to the given line."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            script, revision = self._get_revision(session, show_id)
            if script is None:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return
            if revision is None:
                self.set_status(400)
                await self.finish(
                    {"message": "Script does not have a current revision"}
                )
                return

            data = escape.json_decode(self.request.body)

            cue_type_id: int = data.get("cueTypeId", None)
            if not cue_type_id:
                self.set_status(400)
                await self.finish({"message": ERROR_CUE_TYPE_MISSING})
                return

            cue_type: CueType = session.get(CueType, cue_type_id)
            if not cue_type:
                self.set_status(400)
                await self.finish({"message": ERROR_CUE_TYPE_NOT_FOUND})
                return
            self.requires_role(cue_type, Role.WRITE)

            line_id: int = data.get("lineId", None)
            if not line_id:
                self.set_status(400)
                await self.finish({"message": ERROR_LINE_ID_MISSING})
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

            cues_data: list = data.get("cues", [])
            if not cues_data:
                self.set_status(400)
                await self.finish({"message": ERROR_CUE_GROUP_EMPTY})
                return

            label_override: str | None = data.get("labelOverride") or None

            group = CueGroup(cue_type_id=cue_type_id, label_override=label_override)
            session.add(group)
            session.flush()

            for cue_entry in cues_data:
                ident: str = cue_entry.get("ident", "")
                sort_order: int = cue_entry.get("sortOrder", 0)
                cue = Cue(cue_type_id=cue_type_id, ident=ident)
                session.add(cue)
                session.flush()
                session.add(
                    CueAssociation(
                        revision_id=revision.id,
                        line_id=line_id,
                        cue_id=cue.id,
                        group_id=group.id,
                        sort_order=sort_order,
                    )
                )

            session.commit()
            self.set_status(200)
            await self.finish(
                {"id": group.id, "message": "Successfully added cue group"}
            )
            await self.application.ws_send_to_all("NOOP", "LOAD_CUES", {})

    @requires_show
    @no_live_session
    async def patch(self):
        """Edit an existing cue group — update label and reconcile cue membership."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            script, revision = self._get_revision(session, show_id)
            if script is None:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return
            if revision is None:
                self.set_status(400)
                await self.finish(
                    {"message": "Script does not have a current revision"}
                )
                return

            data = escape.json_decode(self.request.body)

            group_id_raw: int = data.get("groupId", None)
            if not group_id_raw:
                self.set_status(400)
                await self.finish({"message": ERROR_CUE_GROUP_ID_MISSING})
                return

            group: CueGroup = session.get(CueGroup, group_id_raw)
            if not group:
                self.set_status(404)
                await self.finish({"message": ERROR_CUE_GROUP_NOT_FOUND})
                return

            cue_type: CueType = session.get(CueType, group.cue_type_id)
            self.requires_role(cue_type, Role.WRITE)

            line_id: int = data.get("lineId", None)
            if not line_id:
                self.set_status(400)
                await self.finish({"message": ERROR_LINE_ID_MISSING})
                return

            cues_data: list = data.get("cues", [])
            if not cues_data:
                self.set_status(400)
                await self.finish({"message": ERROR_CUE_GROUP_EMPTY})
                return

            # Fork the CueGroup if it is referenced by associations in other revisions
            other_revision_refs = session.scalar(
                select(func.count())
                .select_from(CueAssociation)
                .where(
                    CueAssociation.group_id == group.id,
                    CueAssociation.revision_id != revision.id,
                )
            )
            if other_revision_refs:
                new_group = CueGroup(
                    cue_type_id=group.cue_type_id,
                    label_override=data.get("labelOverride") or None,
                )
                session.add(new_group)
                session.flush()
                # Reassign all current revision's associations to the new group
                current_assocs: List[CueAssociation] = session.scalars(
                    select(CueAssociation).where(
                        CueAssociation.group_id == group.id,
                        CueAssociation.revision_id == revision.id,
                    )
                ).all()
                for assoc in current_assocs:
                    assoc.group_id = new_group.id
                group = new_group
            else:
                group.label_override = data.get("labelOverride") or None

            # Build map of existing associations for this group on this line
            existing_assocs: List[CueAssociation] = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.group_id == group.id,
                    CueAssociation.revision_id == revision.id,
                    CueAssociation.line_id == line_id,
                )
            ).all()
            existing_by_cue_id = {a.cue_id: a for a in existing_assocs}

            requested_cue_ids = set()
            for cue_entry in cues_data:
                cue_id_raw = cue_entry.get("id", None)
                ident: str = cue_entry.get("ident", "")
                sort_order: int = cue_entry.get("sortOrder", 0)

                if cue_id_raw and cue_id_raw in existing_by_cue_id:
                    # Update existing member — ident/sort_order change; cue fork if shared
                    assoc = existing_by_cue_id[cue_id_raw]
                    cue: Cue = assoc.cue
                    requested_cue_ids.add(cue_id_raw)
                    assoc.sort_order = sort_order
                    if len(cue.revision_associations) == 1:
                        cue.ident = ident
                    else:
                        # Fork: create a new Cue; the existing association carries group_id
                        new_cue = Cue(cue_type_id=cue.cue_type_id, ident=ident)
                        session.add(new_cue)
                        session.flush()
                        assoc.cue = new_cue
                else:
                    # New member cue
                    new_cue = Cue(cue_type_id=group.cue_type_id, ident=ident)
                    session.add(new_cue)
                    session.flush()
                    session.add(
                        CueAssociation(
                            revision_id=revision.id,
                            line_id=line_id,
                            cue_id=new_cue.id,
                            group_id=group.id,
                            sort_order=sort_order,
                        )
                    )

            # Delete removed members
            removed_cue_ids = []
            for cue_id_key, assoc in existing_by_cue_id.items():
                if cue_id_key not in requested_cue_ids:
                    removed_cue_ids.append(cue_id_key)
                    session.delete(assoc)

            if removed_cue_ids:
                session.flush()
                for cue_id in removed_cue_ids:
                    CueAssociation.cleanup_orphaned_cue(session, cue_id, flush=False)

            session.commit()
            self.set_status(200)
            await self.finish({"message": "Successfully edited cue group"})
            await self.application.ws_send_to_all("NOOP", "LOAD_CUES", {})

    @requires_show
    @no_live_session
    async def delete(self):
        """Delete a cue group and all its member cues from the given line."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            script, revision = self._get_revision(session, show_id)
            if script is None:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return
            if revision is None:
                self.set_status(400)
                await self.finish(
                    {"message": "Script does not have a current revision"}
                )
                return

            group_id_str = self.get_argument("groupId", None)
            if not group_id_str:
                self.set_status(400)
                await self.finish({"message": ERROR_CUE_GROUP_ID_MISSING})
                return

            try:
                group_id_val = int(group_id_str)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_ID})
                return

            group: CueGroup = session.get(CueGroup, group_id_val)
            if not group:
                self.set_status(404)
                await self.finish({"message": ERROR_CUE_GROUP_NOT_FOUND})
                return

            line_id_str = self.get_argument("lineId", None)
            if not line_id_str:
                self.set_status(400)
                await self.finish({"message": ERROR_LINE_ID_MISSING})
                return

            try:
                line_id_val = int(line_id_str)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_ID})
                return

            cue_type: CueType = session.get(CueType, group.cue_type_id)
            self.requires_role(cue_type, Role.WRITE)

            assocs: List[CueAssociation] = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.group_id == group_id_val,
                    CueAssociation.revision_id == revision.id,
                    CueAssociation.line_id == line_id_val,
                )
            ).all()

            cue_ids = [a.cue_id for a in assocs]
            for assoc in assocs:
                session.delete(assoc)

            # Flush deletions so orphan checks below see the correct counts
            session.flush()

            for cue_id in cue_ids:
                CueAssociation.cleanup_orphaned_cue(session, cue_id, flush=False)

            remaining = (
                session.scalar(
                    select(func.count())
                    .select_from(CueAssociation)
                    .where(CueAssociation.group_id == group_id_val)
                )
                or 0
            )
            if not remaining:
                session.delete(group)

            session.commit()
            self.set_status(200)
            await self.finish({"message": "Successfully deleted cue group"})
            await self.application.ws_send_to_all("NOOP", "LOAD_CUES", {})
