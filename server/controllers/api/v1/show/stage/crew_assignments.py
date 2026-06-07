"""
API controller for crew assignments to props/scenery items.

Crew assignments track which crew members are responsible for setting (bringing on stage)
or striking (removing from stage) props and scenery items at specific scene boundaries.
"""

from sqlalchemy import select
from tornado import escape

from controllers.api.constants import (
    ERROR_ASSIGNMENT_TYPE_INVALID,
    ERROR_ASSIGNMENT_TYPE_MISSING,
    ERROR_CREW_ASSIGNMENT_EXISTS,
    ERROR_CREW_ASSIGNMENT_NOT_FOUND,
    ERROR_CREW_ID_MISSING,
    ERROR_CREW_NOT_FOUND,
    ERROR_ID_MISSING,
    ERROR_INVALID_BOUNDARY,
    ERROR_INVALID_ID,
    ERROR_ITEM_ID_BOTH,
    ERROR_ITEM_ID_MISSING,
    ERROR_PROP_NOT_FOUND,
    ERROR_SCENE_ID_MISSING,
    ERROR_SCENE_NOT_FOUND,
    ERROR_SCENERY_NOT_FOUND,
    ERROR_SHOW_NOT_FOUND,
)
from models.show import Scene, Show
from models.stage import Crew, CrewAssignment, Props, Scenery
from rbac.role import Role
from schemas.schemas import CrewAssignmentSchema
from utils.show.block_computation import is_valid_boundary
from utils.web.base_controller import BaseAPIController
from utils.web.route import ApiRoute, ApiVersion
from utils.web.web_decorators import no_live_session, requires_show


@ApiRoute("show/stage/crew/assignments", ApiVersion.V1)
class CrewAssignmentController(BaseAPIController):
    """Controller for crew assignment CRUD operations."""

    @requires_show
    def get(self):
        """Get all crew assignments for the current show."""
        current_show = self.get_current_show()
        show_id = current_show["id"]
        schema = CrewAssignmentSchema()

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return

            # Get all assignments for crew members in this show
            assignments = session.scalars(
                select(CrewAssignment).join(Crew).where(Crew.show_id == show_id)
            ).all()

            result = [schema.dump(a) for a in assignments]
            self.set_status(200)
            self.finish({"assignments": result})

    @requires_show
    @no_live_session
    async def post(self):
        """
        Create a new crew assignment.

        Required body fields:
        - crew_id: ID of the crew member
        - scene_id: ID of the scene (must be a valid block boundary)
        - assignment_type: 'set' or 'strike'
        - prop_id OR scenery_id: ID of the item (exactly one required)
        """
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return

            self.requires_role(show, Role.WRITE)
            data = escape.json_decode(self.request.body)

            # Validate crew_id
            crew_id = data.get("crew_id")
            if crew_id is None:
                self.set_status(400)
                await self.finish({"message": ERROR_CREW_ID_MISSING})
                return

            try:
                crew_id = int(crew_id)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_ID})
                return

            crew = session.get(Crew, crew_id)
            if not crew or crew.show_id != show_id:
                self.set_status(404)
                await self.finish({"message": ERROR_CREW_NOT_FOUND})
                return

            # Validate scene_id
            scene_id = data.get("scene_id")
            if scene_id is None:
                self.set_status(400)
                await self.finish({"message": ERROR_SCENE_ID_MISSING})
                return

            try:
                scene_id = int(scene_id)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_ID})
                return

            scene = session.get(Scene, scene_id)
            if not scene or scene.show_id != show_id:
                self.set_status(404)
                await self.finish({"message": ERROR_SCENE_NOT_FOUND})
                return

            # Validate assignment_type
            assignment_type = data.get("assignment_type")
            if not assignment_type:
                self.set_status(400)
                await self.finish({"message": ERROR_ASSIGNMENT_TYPE_MISSING})
                return

            if assignment_type not in ("set", "strike"):
                self.set_status(400)
                await self.finish({"message": ERROR_ASSIGNMENT_TYPE_INVALID})
                return

            # Validate prop_id/scenery_id (exactly one must be provided)
            prop_id = data.get("prop_id")
            scenery_id = data.get("scenery_id")

            if prop_id is None and scenery_id is None:
                self.set_status(400)
                await self.finish({"message": ERROR_ITEM_ID_MISSING})
                return

            if prop_id is not None and scenery_id is not None:
                self.set_status(400)
                await self.finish({"message": ERROR_ITEM_ID_BOTH})
                return

            # Validate the item exists and belongs to the show
            if prop_id is not None:
                try:
                    prop_id = int(prop_id)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": ERROR_INVALID_ID})
                    return

                prop = session.get(Props, prop_id)
                if not prop or prop.show_id != show_id:
                    self.set_status(404)
                    await self.finish({"message": ERROR_PROP_NOT_FOUND})
                    return
                scenery_id = None
            else:
                try:
                    scenery_id = int(scenery_id)
                except ValueError:
                    self.set_status(400)
                    await self.finish({"message": ERROR_INVALID_ID})
                    return

                scenery = session.get(Scenery, scenery_id)
                if not scenery or scenery.show_id != show_id:
                    self.set_status(404)
                    await self.finish({"message": ERROR_SCENERY_NOT_FOUND})
                    return
                prop_id = None

            # Validate that the scene is a valid boundary for this assignment
            if not is_valid_boundary(
                session, scene_id, assignment_type, prop_id, scenery_id, show
            ):
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_BOUNDARY})
                return

            # Check for duplicate assignment
            existing_query = select(CrewAssignment).where(
                CrewAssignment.crew_id == crew_id,
                CrewAssignment.scene_id == scene_id,
                CrewAssignment.assignment_type == assignment_type,
            )
            if prop_id is not None:
                existing_query = existing_query.where(CrewAssignment.prop_id == prop_id)
            else:
                existing_query = existing_query.where(
                    CrewAssignment.scenery_id == scenery_id
                )

            existing = session.scalars(existing_query).first()
            if existing:
                self.set_status(400)
                await self.finish({"message": ERROR_CREW_ASSIGNMENT_EXISTS})
                return

            # Create the assignment
            assignment = CrewAssignment(
                crew_id=crew_id,
                scene_id=scene_id,
                assignment_type=assignment_type,
                prop_id=prop_id,
                scenery_id=scenery_id,
            )
            session.add(assignment)
            session.commit()

            self.set_status(200)
            await self.finish(
                {"id": assignment.id, "message": "Successfully created crew assignment"}
            )

            await self.application.ws_send_to_all("NOOP", "GET_CREW_ASSIGNMENTS", {})

    @requires_show
    @no_live_session
    async def patch(self):
        """
        Update an existing crew assignment.

        Required body fields:
        - id: ID of the assignment to update

        Optional body fields (provide any to update):
        - crew_id: New crew member ID
        - scene_id: New scene ID (must be valid boundary for item/type)
        - assignment_type: New assignment type ('set' or 'strike')
        - prop_id: New prop ID (clears scenery_id)
        - scenery_id: New scenery ID (clears prop_id)
        """
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return

            self.requires_role(show, Role.WRITE)
            data = escape.json_decode(self.request.body)

            # Get the assignment to update
            assignment_id = data.get("id")
            if assignment_id is None:
                self.set_status(400)
                await self.finish({"message": ERROR_ID_MISSING})
                return

            try:
                assignment_id = int(assignment_id)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_ID})
                return

            assignment = session.get(CrewAssignment, assignment_id)
            if not assignment:
                self.set_status(404)
                await self.finish({"message": ERROR_CREW_ASSIGNMENT_NOT_FOUND})
                return

            # Verify the assignment belongs to this show
            crew = session.get(Crew, assignment.crew_id)
            if not crew or crew.show_id != show_id:
                self.set_status(404)
                await self.finish({"message": ERROR_CREW_ASSIGNMENT_NOT_FOUND})
                return

            # Collect the new values (use existing if not provided)
            new_crew_id = assignment.crew_id
            new_scene_id = assignment.scene_id
            new_assignment_type = assignment.assignment_type
            new_prop_id = assignment.prop_id
            new_scenery_id = assignment.scenery_id

            # Update crew_id if provided
            if "crew_id" in data:
                try:
                    new_crew_id = int(data["crew_id"])
                except (ValueError, TypeError):
                    self.set_status(400)
                    await self.finish({"message": ERROR_INVALID_ID})
                    return

                new_crew = session.get(Crew, new_crew_id)
                if not new_crew or new_crew.show_id != show_id:
                    self.set_status(404)
                    await self.finish({"message": ERROR_CREW_NOT_FOUND})
                    return

            # Update scene_id if provided
            if "scene_id" in data:
                try:
                    new_scene_id = int(data["scene_id"])
                except (ValueError, TypeError):
                    self.set_status(400)
                    await self.finish({"message": ERROR_INVALID_ID})
                    return

                new_scene = session.get(Scene, new_scene_id)
                if not new_scene or new_scene.show_id != show_id:
                    self.set_status(404)
                    await self.finish({"message": ERROR_SCENE_NOT_FOUND})
                    return

            # Update assignment_type if provided
            if "assignment_type" in data:
                new_assignment_type = data["assignment_type"]
                if new_assignment_type not in ("set", "strike"):
                    self.set_status(400)
                    await self.finish({"message": ERROR_ASSIGNMENT_TYPE_INVALID})
                    return

            # Update prop_id/scenery_id if provided (XOR logic)
            if "prop_id" in data or "scenery_id" in data:
                new_prop_id = data.get("prop_id")
                new_scenery_id = data.get("scenery_id")

                if new_prop_id is None and new_scenery_id is None:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ITEM_ID_MISSING})
                    return

                if new_prop_id is not None and new_scenery_id is not None:
                    self.set_status(400)
                    await self.finish({"message": ERROR_ITEM_ID_BOTH})
                    return

                if new_prop_id is not None:
                    try:
                        new_prop_id = int(new_prop_id)
                    except (ValueError, TypeError):
                        self.set_status(400)
                        await self.finish({"message": ERROR_INVALID_ID})
                        return

                    prop = session.get(Props, new_prop_id)
                    if not prop or prop.show_id != show_id:
                        self.set_status(404)
                        await self.finish({"message": ERROR_PROP_NOT_FOUND})
                        return
                    new_scenery_id = None
                else:
                    try:
                        new_scenery_id = int(new_scenery_id)
                    except (ValueError, TypeError):
                        self.set_status(400)
                        await self.finish({"message": ERROR_INVALID_ID})
                        return

                    scenery = session.get(Scenery, new_scenery_id)
                    if not scenery or scenery.show_id != show_id:
                        self.set_status(404)
                        await self.finish({"message": ERROR_SCENERY_NOT_FOUND})
                        return
                    new_prop_id = None

            # Validate the new combination is a valid boundary
            if not is_valid_boundary(
                session,
                new_scene_id,
                new_assignment_type,
                new_prop_id,
                new_scenery_id,
                show,
            ):
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_BOUNDARY})
                return

            # Check for duplicate assignment (excluding self)
            existing_query = select(CrewAssignment).where(
                CrewAssignment.id != assignment_id,
                CrewAssignment.crew_id == new_crew_id,
                CrewAssignment.scene_id == new_scene_id,
                CrewAssignment.assignment_type == new_assignment_type,
            )
            if new_prop_id is not None:
                existing_query = existing_query.where(
                    CrewAssignment.prop_id == new_prop_id
                )
            else:
                existing_query = existing_query.where(
                    CrewAssignment.scenery_id == new_scenery_id
                )

            existing = session.scalars(existing_query).first()
            if existing:
                self.set_status(400)
                await self.finish({"message": ERROR_CREW_ASSIGNMENT_EXISTS})
                return

            # Apply updates
            assignment.crew_id = new_crew_id
            assignment.scene_id = new_scene_id
            assignment.assignment_type = new_assignment_type
            assignment.prop_id = new_prop_id
            assignment.scenery_id = new_scenery_id

            session.commit()

            self.set_status(200)
            await self.finish({"message": "Successfully updated crew assignment"})

            await self.application.ws_send_to_all("NOOP", "GET_CREW_ASSIGNMENTS", {})

    @requires_show
    @no_live_session
    async def delete(self):
        """Delete a crew assignment by ID (query parameter)."""
        current_show = self.get_current_show()
        show_id = current_show["id"]

        with self.make_session() as session:
            show = session.get(Show, show_id)
            if not show:
                self.set_status(404)
                await self.finish({"message": ERROR_SHOW_NOT_FOUND})
                return

            self.requires_role(show, Role.WRITE)

            assignment_id_str = self.get_argument("id", None)
            if not assignment_id_str:
                self.set_status(400)
                await self.finish({"message": ERROR_ID_MISSING})
                return

            try:
                assignment_id = int(assignment_id_str)
            except ValueError:
                self.set_status(400)
                await self.finish({"message": ERROR_INVALID_ID})
                return

            assignment = session.get(CrewAssignment, assignment_id)
            if not assignment:
                self.set_status(404)
                await self.finish({"message": ERROR_CREW_ASSIGNMENT_NOT_FOUND})
                return

            # Verify the assignment belongs to a crew member in this show
            crew = session.get(Crew, assignment.crew_id)
            if not crew or crew.show_id != show_id:
                self.set_status(404)
                await self.finish({"message": ERROR_CREW_ASSIGNMENT_NOT_FOUND})
                return

            session.delete(assignment)
            session.commit()

            self.set_status(200)
            await self.finish({"message": "Successfully deleted crew assignment"})

            await self.application.ws_send_to_all("NOOP", "GET_CREW_ASSIGNMENTS", {})
