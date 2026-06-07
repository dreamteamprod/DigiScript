"""Unit tests for crew assignments API controller."""

import tornado.escape
from tornado.httpclient import HTTPRequest
from tornado.testing import gen_test

from models.stage import (
    Crew,
    CrewAssignment,
    Props,
    PropsAllocation,
    Scenery,
    SceneryAllocation,
)
from test.conftest import DigiScriptTestCase
from test.helpers.stage_fixtures import (
    create_act_with_scenes,
    create_admin_user,
    create_crew,
    create_prop,
    create_scenery,
    create_show,
)


class TestCrewAssignmentController(DigiScriptTestCase):
    """Test suite for /api/v1/show/stage/crew/assignments endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            self.show_id = create_show(session)
            _, scene_ids = create_act_with_scenes(
                session,
                self.show_id,
                "Act 1",
                3,
                link_to_show=True,
            )
            self.scene1_id, self.scene2_id, self.scene3_id = scene_ids

            self.crew_id = create_crew(session, self.show_id)
            self.prop_type_id, self.prop_id = create_prop(session, self.show_id)
            self.scenery_type_id, self.scenery_id = create_scenery(
                session, self.show_id
            )

            # Allocate prop to scenes 1 and 2 (forms one block)
            # SET boundary: scene 1, STRIKE boundary: scene 2
            allocation1 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene1_id
            )
            allocation2 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene2_id
            )
            session.add_all([allocation1, allocation2])

            # Allocate scenery to scene 3 only (single-scene block)
            allocation3 = SceneryAllocation(
                scenery_id=self.scenery_id, scene_id=self.scene3_id
            )
            session.add(allocation3)

            self.user_id = create_admin_user(session)
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    # =========================================================================
    # GET Tests
    # =========================================================================

    def test_get_assignments_empty(self):
        """Test GET with no assignments returns empty list."""
        response = self.fetch("/api/v1/show/stage/crew/assignments")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("assignments", response_body)
        self.assertEqual([], response_body["assignments"])

    def test_get_assignments_returns_all(self):
        """Test GET returns all assignments for the show."""
        # Create an assignment
        with self._app.get_db().sessionmaker() as session:
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene1_id,
                assignment_type="set",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.commit()

        response = self.fetch("/api/v1/show/stage/crew/assignments")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(1, len(response_body["assignments"]))
        self.assertEqual(self.crew_id, response_body["assignments"][0]["crew_id"])
        self.assertEqual(self.scene1_id, response_body["assignments"][0]["scene_id"])
        self.assertEqual("set", response_body["assignments"][0]["assignment_type"])
        self.assertEqual(self.prop_id, response_body["assignments"][0]["prop_id"])

    def test_get_assignments_no_show(self):
        """Test GET returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch("/api/v1/show/stage/crew/assignments")
        self.assertEqual(400, response.code)

    # =========================================================================
    # POST Tests - Basic Creation
    # =========================================================================

    @gen_test
    async def test_create_assignment_for_prop(self):
        """Test POST creates a new crew assignment for a prop."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene1_id,
                    "assignment_type": "set",
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request)
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("id", response_body)
        self.assertIn("message", response_body)

        # Verify assignment was created
        with self._app.get_db().sessionmaker() as session:
            assignment = session.get(CrewAssignment, response_body["id"])
            self.assertIsNotNone(assignment)
            self.assertEqual(self.crew_id, assignment.crew_id)
            self.assertEqual(self.scene1_id, assignment.scene_id)
            self.assertEqual("set", assignment.assignment_type)
            self.assertEqual(self.prop_id, assignment.prop_id)
            self.assertIsNone(assignment.scenery_id)

    @gen_test
    async def test_create_assignment_for_scenery(self):
        """Test POST creates a new crew assignment for scenery."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene3_id,
                    "assignment_type": "set",
                    "scenery_id": self.scenery_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request)
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("id", response_body)

        # Verify assignment was created
        with self._app.get_db().sessionmaker() as session:
            assignment = session.get(CrewAssignment, response_body["id"])
            self.assertIsNotNone(assignment)
            self.assertIsNone(assignment.prop_id)
            self.assertEqual(self.scenery_id, assignment.scenery_id)

    @gen_test
    async def test_create_assignment_strike(self):
        """Test POST creates a strike assignment."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene2_id,  # Valid STRIKE boundary
                    "assignment_type": "strike",
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request)
        self.assertEqual(200, response.code)

    # =========================================================================
    # POST Tests - Validation Errors
    # =========================================================================

    @gen_test
    async def test_create_assignment_missing_crew_id(self):
        """Test POST returns 400 when crew_id is missing."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "scene_id": self.scene1_id,
                    "assignment_type": "set",
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("crew_id missing", response_body["message"])

    @gen_test
    async def test_create_assignment_missing_scene_id(self):
        """Test POST returns 400 when scene_id is missing."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "assignment_type": "set",
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Scene ID missing", response_body["message"])

    @gen_test
    async def test_create_assignment_missing_assignment_type(self):
        """Test POST returns 400 when assignment_type is missing."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene1_id,
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("assignment_type missing", response_body["message"])

    @gen_test
    async def test_create_assignment_invalid_assignment_type(self):
        """Test POST returns 400 for invalid assignment_type."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene1_id,
                    "assignment_type": "invalid",
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("'set' or 'strike'", response_body["message"])

    @gen_test
    async def test_create_assignment_missing_item_id(self):
        """Test POST returns 400 when neither prop_id nor scenery_id is provided."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene1_id,
                    "assignment_type": "set",
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Either prop_id or scenery_id", response_body["message"])

    @gen_test
    async def test_create_assignment_both_item_ids(self):
        """Test POST returns 400 when both prop_id and scenery_id are provided."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene1_id,
                    "assignment_type": "set",
                    "prop_id": self.prop_id,
                    "scenery_id": self.scenery_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Only one of prop_id or scenery_id", response_body["message"])

    @gen_test
    async def test_create_assignment_invalid_boundary(self):
        """Test POST returns 400 for scene that is not a valid boundary."""
        # Scene 2 is valid STRIKE but not valid SET for the prop
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene2_id,  # Not a valid SET boundary
                    "assignment_type": "set",
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("not a valid boundary", response_body["message"])

    @gen_test
    async def test_create_assignment_unallocated_scene(self):
        """Test POST returns 400 for scene where item is not allocated."""
        # Scene 3 has no prop allocation
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene3_id,
                    "assignment_type": "set",
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("not a valid boundary", response_body["message"])

    @gen_test
    async def test_create_assignment_crew_not_found(self):
        """Test POST returns 404 for non-existent crew member."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": 99999,
                    "scene_id": self.scene1_id,
                    "assignment_type": "set",
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("crew member not found", response_body["message"])

    @gen_test
    async def test_create_assignment_prop_not_found(self):
        """Test POST returns 404 for non-existent prop."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene1_id,
                    "assignment_type": "set",
                    "prop_id": 99999,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("prop not found", response_body["message"])

    @gen_test
    async def test_create_assignment_duplicate(self):
        """Test POST returns 400 for duplicate assignment."""
        # Create first assignment
        with self._app.get_db().sessionmaker() as session:
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene1_id,
                assignment_type="set",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.commit()

        # Try to create duplicate
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "crew_id": self.crew_id,
                    "scene_id": self.scene1_id,
                    "assignment_type": "set",
                    "prop_id": self.prop_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("already exists", response_body["message"])

    # =========================================================================
    # PATCH Tests
    # =========================================================================

    @gen_test
    async def test_update_assignment_crew_id(self):
        """Test PATCH can update crew_id."""
        # Create a second crew member
        with self._app.get_db().sessionmaker() as session:
            crew2 = Crew(show_id=self.show_id, first_name="Jane", last_name="Smith")
            session.add(crew2)
            session.flush()
            crew2_id = crew2.id

            # Create assignment
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene1_id,
                assignment_type="set",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.flush()
            assignment_id = assignment.id
            session.commit()

        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="PATCH",
            body=tornado.escape.json_encode({"id": assignment_id, "crew_id": crew2_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request)
        self.assertEqual(200, response.code)

        # Verify update
        with self._app.get_db().sessionmaker() as session:
            assignment = session.get(CrewAssignment, assignment_id)
            self.assertEqual(crew2_id, assignment.crew_id)

    @gen_test
    async def test_update_assignment_assignment_type(self):
        """Test PATCH can update assignment_type if new scene is valid boundary."""
        # Create assignment for SET at scene 1
        with self._app.get_db().sessionmaker() as session:
            # Create single-scene allocation for scene 3 so it's valid for both
            allocation = PropsAllocation(props_id=self.prop_id, scene_id=self.scene3_id)
            session.add(allocation)
            session.flush()

            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene3_id,  # Single-scene block - valid for both
                assignment_type="set",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.flush()
            assignment_id = assignment.id
            session.commit()

        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": assignment_id, "assignment_type": "strike"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request)
        self.assertEqual(200, response.code)

        # Verify update
        with self._app.get_db().sessionmaker() as session:
            assignment = session.get(CrewAssignment, assignment_id)
            self.assertEqual("strike", assignment.assignment_type)

    @gen_test
    async def test_update_assignment_invalid_new_boundary(self):
        """Test PATCH returns 400 when new combination is invalid boundary."""
        # Create assignment for SET at scene 1
        with self._app.get_db().sessionmaker() as session:
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene1_id,
                assignment_type="set",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.flush()
            assignment_id = assignment.id
            session.commit()

        # Try to change to STRIKE at scene 1 (not valid - scene 2 is STRIKE boundary)
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": assignment_id, "assignment_type": "strike"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("not a valid boundary", response_body["message"])

    @gen_test
    async def test_update_assignment_not_found(self):
        """Test PATCH returns 404 for non-existent assignment."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="PATCH",
            body=tornado.escape.json_encode({"id": 99999, "crew_id": self.crew_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(404, response.code)

    @gen_test
    async def test_update_assignment_missing_id(self):
        """Test PATCH returns 400 when id is missing."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="PATCH",
            body=tornado.escape.json_encode({"crew_id": self.crew_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    # =========================================================================
    # DELETE Tests
    # =========================================================================

    @gen_test
    async def test_delete_assignment_success(self):
        """Test DELETE removes an assignment."""
        with self._app.get_db().sessionmaker() as session:
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene1_id,
                assignment_type="set",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.flush()
            assignment_id = assignment.id
            session.commit()

        request = HTTPRequest(
            self.get_url(f"/api/v1/show/stage/crew/assignments?id={assignment_id}"),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request)
        self.assertEqual(200, response.code)

        # Verify deletion
        with self._app.get_db().sessionmaker() as session:
            assignment = session.get(CrewAssignment, assignment_id)
            self.assertIsNone(assignment)

    @gen_test
    async def test_delete_assignment_not_found(self):
        """Test DELETE returns 404 for non-existent assignment."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments?id=99999"),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(404, response.code)

    @gen_test
    async def test_delete_assignment_missing_id(self):
        """Test DELETE returns 400 when ID is missing."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments"),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    @gen_test
    async def test_delete_assignment_invalid_id(self):
        """Test DELETE returns 400 for non-integer ID."""
        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/crew/assignments?id=invalid"),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request, raise_error=False)
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid ID", response_body["message"])


class TestCrewAssignmentCascadeDelete(DigiScriptTestCase):
    """Test suite for CASCADE delete behavior on crew assignments."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            self.show_id = create_show(session)
            _, scene_ids = create_act_with_scenes(
                session,
                self.show_id,
                "Act 1",
                1,
                link_to_show=True,
            )
            self.scene_id = scene_ids[0]

            self.crew_id = create_crew(session, self.show_id)
            _, self.prop_id = create_prop(session, self.show_id)

            # Allocate prop to scene
            allocation = PropsAllocation(props_id=self.prop_id, scene_id=self.scene_id)
            session.add(allocation)

            # Create assignment
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene_id,
                assignment_type="set",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.flush()
            self.assignment_id = assignment.id

            self.user_id = create_admin_user(session)
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def test_cascade_delete_on_crew_delete(self):
        """Test assignment is deleted when crew member is deleted."""
        # Delete the crew member
        with self._app.get_db().sessionmaker() as session:
            crew = session.get(Crew, self.crew_id)
            session.delete(crew)
            session.commit()

            # Verify assignment was cascade deleted
            assignment = session.get(CrewAssignment, self.assignment_id)
            self.assertIsNone(assignment)

    def test_cascade_delete_on_prop_delete(self):
        """Test assignment is deleted when prop is deleted."""
        # Delete the prop
        with self._app.get_db().sessionmaker() as session:
            prop = session.get(Props, self.prop_id)
            session.delete(prop)
            session.commit()

            # Verify assignment was cascade deleted
            assignment = session.get(CrewAssignment, self.assignment_id)
            self.assertIsNone(assignment)

    def test_cascade_delete_on_scenery_delete(self):
        """Test assignment is deleted when scenery is deleted."""
        # Create a scenery item and assignment
        with self._app.get_db().sessionmaker() as session:
            _, scenery_id = create_scenery(session, self.show_id, name="Wall")

            # Allocate scenery to scene
            allocation = SceneryAllocation(
                scenery_id=scenery_id, scene_id=self.scene_id
            )
            session.add(allocation)

            # Create assignment for scenery
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene_id,
                assignment_type="set",
                scenery_id=scenery_id,
            )
            session.add(assignment)
            session.flush()
            assignment_id = assignment.id
            session.commit()

        # Delete the scenery
        with self._app.get_db().sessionmaker() as session:
            scenery = session.get(Scenery, scenery_id)
            session.delete(scenery)
            session.commit()

            # Verify assignment was cascade deleted
            assignment = session.get(CrewAssignment, assignment_id)
            self.assertIsNone(assignment)


class TestOrphanDeletionOnAllocationChange(DigiScriptTestCase):
    """Test suite for orphan deletion when allocations change."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            self.show_id = create_show(session)
            _, scene_ids = create_act_with_scenes(
                session,
                self.show_id,
                "Act 1",
                3,
                link_to_show=True,
            )
            self.scene1_id, self.scene2_id, self.scene3_id = scene_ids

            self.crew_id = create_crew(session, self.show_id)
            _, self.prop_id = create_prop(session, self.show_id)

            # Allocate prop to scenes 1 and 2 (block: SET at 1, STRIKE at 2)
            allocation1 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene1_id
            )
            allocation2 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene2_id
            )
            session.add_all([allocation1, allocation2])
            session.flush()
            self.allocation2_id = allocation2.id

            # Create crew assignment at STRIKE boundary (scene 2)
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene2_id,
                assignment_type="strike",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.flush()
            self.assignment_id = assignment.id

            self.user_id = create_admin_user(session)
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    @gen_test
    async def test_orphan_deleted_on_allocation_delete(self):
        """Test crew assignment is deleted when allocation removal invalidates boundary."""
        # Delete allocation at scene 2 via API
        # This should make scene 1 the new STRIKE boundary
        # and orphan the assignment at scene 2
        request = HTTPRequest(
            self.get_url(
                f"/api/v1/show/stage/props/allocations?id={self.allocation2_id}"
            ),
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request)
        self.assertEqual(200, response.code)

        # Verify the crew assignment was orphan-deleted
        with self._app.get_db().sessionmaker() as session:
            assignment = session.get(CrewAssignment, self.assignment_id)
            self.assertIsNone(assignment)

    @gen_test
    async def test_orphan_deleted_on_allocation_create(self):
        """Test crew assignment is deleted when new allocation changes boundaries."""
        # First, set up a scenario where adding allocation creates orphan
        # Current: prop allocated to scenes 1,2 (SET:1, STRIKE:2)
        # Add allocation to scene 3 (new block: scenes 1,2,3, SET:1, STRIKE:3)
        # This makes scene 2 no longer a STRIKE boundary

        request = HTTPRequest(
            self.get_url("/api/v1/show/stage/props/allocations"),
            method="POST",
            body=tornado.escape.json_encode(
                {"props_id": self.prop_id, "scene_id": self.scene3_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        response = await self.http_client.fetch(request)
        self.assertEqual(200, response.code)

        # Verify the crew assignment at scene 2 STRIKE was orphan-deleted
        with self._app.get_db().sessionmaker() as session:
            assignment = session.get(CrewAssignment, self.assignment_id)
            self.assertIsNone(assignment)
