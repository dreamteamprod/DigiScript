from datetime import datetime
from functools import partial
from typing import List, Optional

from sqlalchemy import func
from tornado import escape
from tornado.ioloop import IOLoop

from models.script import (
    CompiledScript,
    Script,
    ScriptCuts,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptRevision,
)
from models.show import Show
from rbac.role import Role
from schemas.schemas import ScriptLineSchema
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("/show/script", ApiVersion.V1)
class ScriptController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        page = self.get_query_argument("page", None)
        if not page:
            self.set_status(400)
            self.finish({"message": "Page not given"})
            return

        page = int(page)

        line_schema = ScriptLineSchema()

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision
                    )
                else:
                    self.set_status(400)
                    self.finish({"message": "Script does not have a current revision"})
                    return

                revision_lines: List[ScriptLineRevisionAssociation] = (
                    session.query(ScriptLineRevisionAssociation)
                    .filter(
                        ScriptLineRevisionAssociation.revision_id == revision.id,
                        ScriptLineRevisionAssociation.line.has(page=page),
                    )
                    .all()
                )

                first_line = None
                for line in revision_lines:
                    if (
                        page == 1
                        and line.previous_line is None
                        or line.previous_line.page == page - 1
                    ):
                        if first_line:
                            self.set_status(400)
                            self.finish(
                                {"message": "Failed to establish page line order"}
                            )
                            return

                        first_line = line

                lines = []
                line_revision = first_line
                while line_revision:
                    if line_revision.line.page != page:
                        break

                    lines.append(line_schema.dump(line_revision.line))
                    line_revision = session.query(ScriptLineRevisionAssociation).get(
                        {
                            "revision_id": revision.id,
                            "line_id": line_revision.next_line_id,
                        }
                    )

                self.set_status(200)
                self.finish({"lines": lines, "page": page})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})
                return

    @staticmethod
    def _validate_line(line_json):
        if line_json["stage_direction"]:
            if len(line_json["line_parts"]) > 1:
                return False, "Stage directions can only have 1 line part"
            line_part = line_json["line_parts"][0]
            if line_part["character_id"] is not None:
                return False, "Stage directions cannot have characters"
            if line_part["character_group_id"] is not None:
                return False, "Stage directions cannot have character groups"
            if line_part["line_text"] is None:
                return False, "Stage directions must contain text"
        else:
            for line_part in line_json["line_parts"]:
                if line_part["line_text"] is None:
                    if len(line_json["line_parts"]) == 1:
                        return False, "Line parts must contain text"
                    if not any(
                        lp["line_text"] is not None for lp in line_json["line_parts"]
                    ):
                        return False, (
                            "At least one line part in a multi part line must "
                            "contain text"
                        )
                if (
                    line_part["character_id"] is None
                    and line_part["character_group_id"] is None
                ):
                    return (
                        False,
                        "Line parts must contain a character or character group",
                    )
                if line_part["character_id"] and line_part["character_group_id"]:
                    return (
                        False,
                        "Line parts cannot contain both a character and character group",
                    )

        return True, ""

    @requires_show
    @no_live_session
    async def post(self):
        page = self.get_query_argument("page", None)
        if not page:
            self.set_status(400)
            await self.finish({"message": "Page not given"})
            return

        page = int(page)

        with self.make_session() as session:
            show = session.query(Show).get(self.get_current_show()["id"])
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )
                self.requires_role(script, Role.WRITE)

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision
                    )
                else:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Script does not have a current revision"}
                    )
                    return

                lines = escape.json_decode(self.request.body)

                previous_line: Optional[ScriptLineRevisionAssociation] = None
                for index, line in enumerate(lines):
                    # Validate each line before we do anything with it
                    valid_status, valid_reason = self._validate_line(line)
                    if not valid_status:
                        session.rollback()
                        self.set_status(400)
                        await self.finish({"message": valid_reason})
                        return

                    # Create the initial line object, and flush it to the database as we need
                    # the ID for further in the loop
                    line_obj = ScriptLine(
                        act_id=line["act_id"],
                        scene_id=line["scene_id"],
                        page=line["page"],
                        stage_direction=line["stage_direction"],
                        stage_direction_style_id=line["stage_direction_style_id"],
                    )
                    session.add(line_obj)
                    session.flush()

                    # Line revision object to keep track of that thing
                    line_revision = ScriptLineRevisionAssociation(
                        revision_id=revision.id, line_id=line_obj.id
                    )
                    session.add(line_revision)
                    session.flush()

                    if index == 0 and page > 1:
                        # First line and not the first page, so need to get the last line of the
                        # previous page and set its next line to this one
                        prev_page_lines: List[ScriptLineRevisionAssociation] = (
                            session.query(ScriptLineRevisionAssociation)
                            .filter(
                                ScriptLineRevisionAssociation.revision_id
                                == revision.id,
                                ScriptLineRevisionAssociation.line.has(page=page - 1),
                            )
                            .all()
                        )

                        if not prev_page_lines:
                            session.rollback()
                            self.set_status(400)
                            await self.finish(
                                {"message": "Previous page does not contain any lines"}
                            )
                            return

                        # Perform some iteration here to establish the first line of the script
                        # of the previous page
                        first_line = None
                        for prev_line in prev_page_lines:
                            if (
                                prev_line.previous_line is None
                                or prev_line.previous_line.page
                                == prev_line.line.page - 1
                            ):
                                if first_line:
                                    session.rollback()
                                    self.set_status(400)
                                    await self.finish(
                                        {
                                            "message": "Failed to establish page line order for "
                                            "previous page"
                                        }
                                    )
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
                            prev_line = session.query(
                                ScriptLineRevisionAssociation
                            ).get(
                                {
                                    "revision_id": revision.id,
                                    "line_id": prev_line.next_line_id,
                                }
                            )

                        previous_lines[-1].next_line_id = line_obj.id
                        line_revision.previous_line_id = previous_lines[-1].line_id
                        session.flush()

                    # Set the next and previous line reference
                    if previous_line:
                        previous_line.next_line = line_obj
                        line_revision.previous_line = previous_line.line
                        session.flush()

                    # Construct the line part objects and add these to the line itself
                    for line_part in line["line_parts"]:
                        part_obj = ScriptLinePart(
                            line_id=line_obj.id,
                            part_index=line_part["part_index"],
                            character_id=line_part["character_id"],
                            character_group_id=line_part["character_group_id"],
                            line_text=line_part["line_text"],
                        )
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

                # Spawn a callback to create a compiled version of the script
                IOLoop.current().add_callback(
                    partial(
                        CompiledScript.compile_script, self.application, revision.id
                    )
                )
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
                return

    @staticmethod
    def _create_new_line(session, revision, line, previous_line, with_association=True):
        # Create the line object
        line_obj = ScriptLine(
            act_id=line["act_id"],
            scene_id=line["scene_id"],
            page=line["page"],
            stage_direction=line["stage_direction"],
            stage_direction_style_id=line["stage_direction_style_id"],
        )
        session.add(line_obj)
        session.flush()

        line_association = None
        if with_association:
            # Line revision object to keep track of that thing
            line_association = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line_obj.id
            )
            session.add(line_association)
            session.flush()

            # Set the next and previous line reference
            if previous_line:
                previous_line.next_line = line_obj
                line_association.previous_line = previous_line.line
                session.flush()

        # Construct the line part objects and add these to the line itself
        for line_part in line["line_parts"]:
            part_obj = ScriptLinePart(
                line_id=line_obj.id,
                part_index=line_part["part_index"],
                character_id=line_part["character_id"],
                character_group_id=line_part["character_group_id"],
                line_text=line_part["line_text"],
            )
            session.add(part_obj)
            line_obj.line_parts.append(part_obj)

        # Flush the DB to add the line parts
        session.flush()

        return line_association, line_obj

    @requires_show
    @no_live_session
    async def patch(self):
        page = self.get_query_argument("page", None)
        if not page:
            self.set_status(400)
            await self.finish({"message": "Page not given"})
            return

        page = int(page)

        with self.make_session() as session:
            show = session.query(Show).get(self.get_current_show()["id"])
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )
                self.requires_role(script, Role.WRITE)

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision
                    )
                else:
                    self.set_status(400)
                    await self.finish(
                        {"message": "Script does not have a current revision"}
                    )
                    return

                request_body = escape.json_decode(self.request.body)

                lines = request_body.get("page", None)
                if lines is None:
                    self.set_status(400)
                    await self.finish(
                        {
                            "message": "Malformed request body, could not find `page` data"
                        }
                    )
                    return

                status = request_body.get("status", None)
                if status is None:
                    self.set_status(400)
                    await self.finish(
                        {
                            "message": "Malformed request body, could not find `status` data"
                        }
                    )
                    return

                # If we are editing a page other than the first page, we need to get the previous
                # line based on the last line from the previous page to ensure that any edits made
                # to the first line of this page are reflected properly
                if page > 1:
                    if lines[0]["id"] is not None:
                        first_line = session.query(ScriptLineRevisionAssociation).get(
                            {"revision_id": revision.id, "line_id": lines[0]["id"]}
                        )

                        if not first_line:
                            session.rollback()
                            self.set_status(400)
                            await self.finish(
                                {"message": "Unable to load line data for first line"}
                            )
                            return

                        if not first_line.previous_line:
                            session.rollback()
                            self.set_status(400)
                            await self.finish(
                                {
                                    "message": "Unable to establish page line order - "
                                    "first line on this page does not have a previous line"
                                }
                            )
                            return

                        previous_line = session.query(
                            ScriptLineRevisionAssociation
                        ).get(
                            {
                                "revision_id": revision.id,
                                "line_id": first_line.previous_line.id,
                            }
                        )

                        if not previous_line:
                            session.rollback()
                            self.set_status(400)
                            await self.finish(
                                {
                                    "message": "Unable to establish page line order - "
                                    "could not find previous line data for first line on this "
                                    "page"
                                }
                            )
                            return
                    else:
                        session.rollback()
                        self.set_status(400)
                        await self.finish(
                            {
                                "message": "Cannot establish line order as first line has "
                                "no ID"
                            }
                        )
                        return
                else:
                    previous_line: Optional[ScriptLineRevisionAssociation] = None

                for index, line in enumerate(lines):
                    if index in status["added"]:
                        # Validate the line
                        valid_status, valid_reason = self._validate_line(line)
                        if not valid_status:
                            session.rollback()
                            self.set_status(400)
                            await self.finish({"message": valid_reason})
                            return

                        line_association, line_object = self._create_new_line(
                            session, revision, line, previous_line
                        )
                        previous_line = line_association
                    elif index in status["inserted"]:
                        # Validate the line
                        valid_status, valid_reason = self._validate_line(line)
                        if not valid_status:
                            session.rollback()
                            self.set_status(400)
                            await self.finish({"message": valid_reason})
                            return

                        line_association, line_object = self._create_new_line(
                            session,
                            revision,
                            line,
                            previous_line,
                            with_association=False,
                        )
                        line_association = ScriptLineRevisionAssociation(
                            revision_id=revision.id, line_id=line_object.id
                        )
                        line_association.previous_line = previous_line.line
                        session.add(line_association)
                        session.flush()

                        if previous_line.next_line:
                            next_association: ScriptLineRevisionAssociation = (
                                session.query(ScriptLineRevisionAssociation).get(
                                    {
                                        "revision_id": revision.id,
                                        "line_id": previous_line.next_line.id,
                                    }
                                )
                            )
                            next_association.previous_line = line_object
                            line_association.next_line = next_association.line

                        previous_line.next_line = line_object

                        session.flush()

                        previous_line = line_association
                    elif index in status["deleted"]:
                        curr_association: ScriptLineRevisionAssociation = session.query(
                            ScriptLineRevisionAssociation
                        ).get({"revision_id": revision.id, "line_id": line["id"]})

                        # Logic for handling next/previous line associations
                        if (
                            curr_association.next_line
                            and curr_association.previous_line
                        ):
                            # Next line and previous line, so need to update both
                            next_association: ScriptLineRevisionAssociation = (
                                session.query(ScriptLineRevisionAssociation).get(
                                    {
                                        "revision_id": revision.id,
                                        "line_id": curr_association.next_line.id,
                                    }
                                )
                            )
                            next_association.previous_line = (
                                curr_association.previous_line
                            )
                            session.flush()

                            prev_association: ScriptLineRevisionAssociation = (
                                session.query(ScriptLineRevisionAssociation).get(
                                    {
                                        "revision_id": revision.id,
                                        "line_id": curr_association.previous_line.id,
                                    }
                                )
                            )
                            prev_association.next_line = next_association.line
                            session.flush()
                        elif curr_association.next_line:
                            # No previous line, so need to update next line only
                            next_association: ScriptLineRevisionAssociation = (
                                session.query(ScriptLineRevisionAssociation).get(
                                    {
                                        "revision_id": revision.id,
                                        "line_id": curr_association.next_line.id,
                                    }
                                )
                            )
                            next_association.previous_line = None
                            session.flush()
                        elif curr_association.previous_line:
                            # No next line, so need to update previous line only
                            prev_association: ScriptLineRevisionAssociation = (
                                session.query(ScriptLineRevisionAssociation).get(
                                    {
                                        "revision_id": revision.id,
                                        "line_id": curr_association.previous_line.id,
                                    }
                                )
                            )
                            prev_association.next_line = None
                            session.flush()
                        session.delete(curr_association)
                    elif index in status["updated"]:
                        # Validate the line
                        valid_status, valid_reason = self._validate_line(line)
                        if not valid_status:
                            session.rollback()
                            self.set_status(400)
                            await self.finish({"message": valid_reason})
                            return

                        curr_association: ScriptLineRevisionAssociation = session.query(
                            ScriptLineRevisionAssociation
                        ).get({"revision_id": revision.id, "line_id": line["id"]})
                        curr_line = curr_association.line

                        if not curr_association:
                            session.rollback()
                            self.set_status(500)
                            await self.finish({"message": "Unable to load line data"})
                            return

                        line_association, line_object = self._create_new_line(
                            session,
                            revision,
                            line,
                            previous_line,
                            with_association=False,
                        )
                        curr_association.line = line_object
                        if previous_line:
                            previous_line.next_line = line_object
                            curr_association.previous_line = previous_line.line

                        if curr_association.next_line:
                            next_association: ScriptLineRevisionAssociation = (
                                session.query(ScriptLineRevisionAssociation).get(
                                    {
                                        "revision_id": revision.id,
                                        "line_id": curr_association.next_line.id,
                                    }
                                )
                            )
                            next_association.previous_line = line_object
                        session.flush()

                        if len(curr_line.revision_associations) == 0:
                            session.delete(curr_line)

                        session.flush()

                        previous_line = curr_association
                    else:
                        previous_line = session.query(
                            ScriptLineRevisionAssociation
                        ).get({"revision_id": revision.id, "line_id": line["id"]})
                # Spawn a callback to create a compiled version of the script
                IOLoop.current().add_callback(
                    partial(
                        CompiledScript.compile_script, self.application, revision.id
                    )
                )
            else:
                self.set_status(404)
                await self.finish({"message": "404 show not found"})
                return


@ApiRoute("/show/script/compiled", ApiVersion.V1)
class CompiledScriptController(BaseAPIController):
    @requires_show
    def get(self):
        with self.make_session() as session:
            show = session.query(Show).get(self.get_current_show()["id"])
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision
                    )
                else:
                    self.set_status(400)
                    self.finish({"message": "Script does not have a current revision"})
                    return

                compiled_script = CompiledScript.load_compiled_script(
                    self.application, revision.id
                )
                if not compiled_script:
                    self.set_status(404)
                    self.finish({"message": "Script does not have a compiled form"})
                    return

                self.set_status(200)
                self.finish(compiled_script)
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})
                return


@ApiRoute("/show/script/cuts", ApiVersion.V1)
class ScriptCutsController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision
                    )
                else:
                    self.set_status(400)
                    self.finish({"message": "Script does not have a current revision"})
                    return

                line_cuts = (
                    session.query(ScriptCuts)
                    .filter(ScriptCuts.revision_id == revision.id)
                    .all()
                )
                line_cuts = [line_cut.line_part_id for line_cut in line_cuts]

                self.set_status(200)
                self.finish({"cuts": line_cuts})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})
                return

    @requires_show
    @no_live_session
    def put(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )
                self.requires_role(script, Role.WRITE)

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision
                    )
                else:
                    self.set_status(400)
                    self.finish({"message": "Script does not have a current revision"})
                    return

                request_body = escape.json_decode(self.request.body)

                cuts = request_body.get("cuts", None)
                if cuts is None:
                    self.set_status(400)
                    self.finish(
                        {
                            "message": "Malformed request body, could not find `cuts` data"
                        }
                    )
                    return

                line_cuts: List[ScriptCuts] = (
                    session.query(ScriptCuts)
                    .filter(ScriptCuts.revision_id == revision.id)
                    .all()
                )

                # Remove any cuts not in the list
                existing_cuts = []
                for cut in line_cuts:
                    if cut.line_part_id not in cuts:
                        session.delete(cut)
                    else:
                        existing_cuts.append(cut.line_part_id)

                # Add new cuts
                cuts_to_add = [cut for cut in cuts if cut not in existing_cuts]
                for cut in cuts_to_add:
                    session.add(
                        ScriptCuts(
                            line_part_id=cut,
                            revision_id=revision.id,
                        )
                    )

                session.commit()


@ApiRoute("/show/script/max_page", ApiVersion.V1)
class ScriptMaxPageController(BaseAPIController):
    @requires_show
    def get(self):
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.query(Show).get(show_id)
            if show:
                script: Script = (
                    session.query(Script).filter(Script.show_id == show.id).first()
                )

                if script.current_revision:
                    revision: ScriptRevision = session.query(ScriptRevision).get(
                        script.current_revision
                    )
                else:
                    self.set_status(400)
                    self.finish({"message": "Script does not have a current revision"})
                    return

                line_ids = (
                    session.query(ScriptLineRevisionAssociation)
                    .with_entities(ScriptLineRevisionAssociation.line_id)
                    .filter(ScriptLineRevisionAssociation.revision_id == revision.id)
                )
                max_page = (
                    session.query(ScriptLine)
                    .with_entities(func.max(ScriptLine.page))
                    .where(ScriptLine.id.in_(line_ids))
                    .first()[0]
                )

                if max_page is None:
                    max_page = 0

                self.set_status(200)
                self.finish({"max_page": max_page})
            else:
                self.set_status(404)
                self.finish({"message": "404 show not found"})
                return
