import tornado.escape

from models.show import Act, Scene, Show, ShowScriptType
from models.stage import Scenery, SceneryAllocation, SceneryType
from models.user import User
from test.conftest import DigiScriptTestCase


class TestSceneryAllocationController(DigiScriptTestCase):
    """Test suite for /api/v1/show/stage/scenery/allocations endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create an act and scene
            act = Act(show_id=show.id, name="Act 1", interval_after=False)
            session.add(act)
            session.flush()
            self.act_id = act.id

            scene = Scene(
                show_id=show.id,
                act_id=act.id,
                name="Scene 1",
                previous_scene_id=None,
            )
            session.add(scene)
            session.flush()
            self.scene_id = scene.id

            # Create a scenery type and scenery
            scenery_type = SceneryType(
                show_id=show.id, name="Backdrops", description=""
            )
            session.add(scenery_type)
            session.flush()
            self.scenery_type_id = scenery_type.id

            scenery = Scenery(
                show_id=show.id,
                scenery_type_id=scenery_type.id,
                name="Forest Backdrop",
                description="Test scenery",
            )
            session.add(scenery)
            session.flush()
            self.scenery_id = scenery.id

            # Create admin user for RBAC
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            self.user_id = admin.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def test_get_allocations_empty(self):
        """Test GET with no allocations returns empty list."""
        response = self.fetch("/api/v1/show/stage/scenery/allocations")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("allocations", response_body)
        self.assertEqual([], response_body["allocations"])

    def test_get_allocations_returns_all(self):
        """Test GET returns all allocations for the show."""
        # Create an allocation
        with self._app.get_db().sessionmaker() as session:
            allocation = SceneryAllocation(
                scenery_id=self.scenery_id, scene_id=self.scene_id
            )
            session.add(allocation)
            session.commit()

        response = self.fetch("/api/v1/show/stage/scenery/allocations")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(1, len(response_body["allocations"]))
        self.assertEqual(self.scenery_id, response_body["allocations"][0]["scenery_id"])
        self.assertEqual(self.scene_id, response_body["allocations"][0]["scene_id"])

    def test_get_allocations_no_show(self):
        """Test GET returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch("/api/v1/show/stage/scenery/allocations")
        self.assertEqual(400, response.code)

    def test_create_allocation_success(self):
        """Test POST creates a new allocation."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"scenery_id": self.scenery_id, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("id", response_body)
        self.assertIn("message", response_body)

        # Verify allocation was created
        with self._app.get_db().sessionmaker() as session:
            allocation = session.get(SceneryAllocation, response_body["id"])
            self.assertIsNotNone(allocation)
            self.assertEqual(self.scenery_id, allocation.scenery_id)
            self.assertEqual(self.scene_id, allocation.scene_id)

    def test_create_allocation_duplicate(self):
        """Test POST returns 400 for duplicate allocation."""
        # Create initial allocation
        with self._app.get_db().sessionmaker() as session:
            allocation = SceneryAllocation(
                scenery_id=self.scenery_id, scene_id=self.scene_id
            )
            session.add(allocation)
            session.commit()

        # Try to create duplicate
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"scenery_id": self.scenery_id, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("already exists", response_body["message"])

    def test_create_allocation_invalid_scenery_id(self):
        """Test POST returns 404 for non-existent scenery."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"scenery_id": 99999, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_create_allocation_invalid_scene_id(self):
        """Test POST returns 404 for non-existent scene."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"scenery_id": self.scenery_id, "scene_id": 99999}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_create_allocation_scenery_wrong_show(self):
        """Test POST returns 404 for scenery from different show."""
        # Create another show with scenery
        with self._app.get_db().sessionmaker() as session:
            other_show = Show(name="Other Show", script_mode=ShowScriptType.FULL)
            session.add(other_show)
            session.flush()

            other_scenery_type = SceneryType(
                show_id=other_show.id, name="Other Type", description=""
            )
            session.add(other_scenery_type)
            session.flush()

            other_scenery = Scenery(
                show_id=other_show.id,
                scenery_type_id=other_scenery_type.id,
                name="Other Scenery",
                description="",
            )
            session.add(other_scenery)
            session.flush()
            other_scenery_id = other_scenery.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"scenery_id": other_scenery_id, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_create_allocation_missing_scenery_id(self):
        """Test POST returns 400 when scenery_id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations",
            method="POST",
            body=tornado.escape.json_encode({"scene_id": self.scene_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("scenery_id missing", response_body["message"])

    def test_create_allocation_missing_scene_id(self):
        """Test POST returns 400 when scene_id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations",
            method="POST",
            body=tornado.escape.json_encode({"scenery_id": self.scenery_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Scene ID missing", response_body["message"])

    def test_create_allocation_no_show(self):
        """Test POST returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"scenery_id": self.scenery_id, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    def test_delete_allocation_success(self):
        """Test DELETE removes an allocation."""
        # Create an allocation
        with self._app.get_db().sessionmaker() as session:
            allocation = SceneryAllocation(
                scenery_id=self.scenery_id, scene_id=self.scene_id
            )
            session.add(allocation)
            session.flush()
            allocation_id = allocation.id
            session.commit()

        response = self.fetch(
            f"/api/v1/show/stage/scenery/allocations?id={allocation_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify allocation was deleted
        with self._app.get_db().sessionmaker() as session:
            allocation = session.get(SceneryAllocation, allocation_id)
            self.assertIsNone(allocation)

    def test_delete_allocation_not_found(self):
        """Test DELETE returns 404 for non-existent allocation."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations?id=99999",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_delete_allocation_missing_id(self):
        """Test DELETE returns 400 when ID is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_delete_allocation_invalid_id(self):
        """Test DELETE returns 400 for non-integer ID."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations?id=invalid",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid ID", response_body["message"])

    def test_delete_allocation_no_show(self):
        """Test DELETE returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/scenery/allocations?id=1",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)


class TestSceneryTypesController(DigiScriptTestCase):
    """Test suite for /api/v1/show/stage/scenery/types endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create admin user for RBAC
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            self.user_id = admin.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    # GET tests

    def test_get_scenery_types_empty(self):
        """Test GET with no scenery types returns empty list."""
        response = self.fetch("/api/v1/show/stage/scenery/types")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("scenery_types", response_body)
        self.assertEqual([], response_body["scenery_types"])

    def test_get_scenery_types_returns_all(self):
        """Test GET returns all scenery types for the show."""
        with self._app.get_db().sessionmaker() as session:
            scenery_type = SceneryType(
                show_id=self.show_id, name="Backdrops", description="Background pieces"
            )
            session.add(scenery_type)
            session.commit()

        response = self.fetch("/api/v1/show/stage/scenery/types")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(1, len(response_body["scenery_types"]))
        self.assertEqual("Backdrops", response_body["scenery_types"][0]["name"])

    def test_get_scenery_types_no_show(self):
        """Test GET returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch("/api/v1/show/stage/scenery/types")
        self.assertEqual(400, response.code)

    # POST tests

    def test_create_scenery_type_success(self):
        """Test POST creates a new scenery type."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="POST",
            body=tornado.escape.json_encode({"name": "Platforms"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("id", response_body)
        self.assertIn("message", response_body)

        # Verify scenery type was created
        with self._app.get_db().sessionmaker() as session:
            scenery_type = session.get(SceneryType, response_body["id"])
            self.assertIsNotNone(scenery_type)
            self.assertEqual("Platforms", scenery_type.name)

    def test_create_scenery_type_with_description(self):
        """Test POST creates a scenery type with description."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="POST",
            body=tornado.escape.json_encode(
                {"name": "Platforms", "description": "Elevated surfaces"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Verify description was saved
        with self._app.get_db().sessionmaker() as session:
            scenery_type = session.get(SceneryType, response_body["id"])
            self.assertEqual("Elevated surfaces", scenery_type.description)

    def test_create_scenery_type_missing_name(self):
        """Test POST returns 400 when name is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="POST",
            body=tornado.escape.json_encode({"description": "Some description"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Name missing", response_body["message"])

    def test_create_scenery_type_no_show(self):
        """Test POST returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="POST",
            body=tornado.escape.json_encode({"name": "Platforms"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    # PATCH tests

    def test_update_scenery_type_success(self):
        """Test PATCH updates an existing scenery type."""
        # Create a scenery type first
        with self._app.get_db().sessionmaker() as session:
            scenery_type = SceneryType(
                show_id=self.show_id, name="Backdrops", description=""
            )
            session.add(scenery_type)
            session.flush()
            scenery_type_id = scenery_type.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": scenery_type_id, "name": "Flats", "description": "Updated"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify update
        with self._app.get_db().sessionmaker() as session:
            scenery_type = session.get(SceneryType, scenery_type_id)
            self.assertEqual("Flats", scenery_type.name)
            self.assertEqual("Updated", scenery_type.description)

    def test_update_scenery_type_missing_id(self):
        """Test PATCH returns 400 when id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="PATCH",
            body=tornado.escape.json_encode({"name": "Flats"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_update_scenery_type_not_found(self):
        """Test PATCH returns 404 for non-existent scenery type."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="PATCH",
            body=tornado.escape.json_encode({"id": 99999, "name": "Flats"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_update_scenery_type_missing_name(self):
        """Test PATCH returns 400 when name is missing."""
        # Create a scenery type first
        with self._app.get_db().sessionmaker() as session:
            scenery_type = SceneryType(
                show_id=self.show_id, name="Backdrops", description=""
            )
            session.add(scenery_type)
            session.flush()
            scenery_type_id = scenery_type.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="PATCH",
            body=tornado.escape.json_encode({"id": scenery_type_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Name missing", response_body["message"])

    def test_update_scenery_type_no_show(self):
        """Test PATCH returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="PATCH",
            body=tornado.escape.json_encode({"id": 1, "name": "Flats"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    # DELETE tests

    def test_delete_scenery_type_success(self):
        """Test DELETE removes a scenery type."""
        # Create a scenery type first
        with self._app.get_db().sessionmaker() as session:
            scenery_type = SceneryType(
                show_id=self.show_id, name="Backdrops", description=""
            )
            session.add(scenery_type)
            session.flush()
            scenery_type_id = scenery_type.id
            session.commit()

        response = self.fetch(
            f"/api/v1/show/stage/scenery/types?id={scenery_type_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify deletion
        with self._app.get_db().sessionmaker() as session:
            scenery_type = session.get(SceneryType, scenery_type_id)
            self.assertIsNone(scenery_type)

    def test_delete_scenery_type_missing_id(self):
        """Test DELETE returns 400 when id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/types",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_delete_scenery_type_invalid_id(self):
        """Test DELETE returns 400 for non-integer ID."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/types?id=invalid",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid ID", response_body["message"])

    def test_delete_scenery_type_not_found(self):
        """Test DELETE returns 404 for non-existent scenery type."""
        response = self.fetch(
            "/api/v1/show/stage/scenery/types?id=99999",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_delete_scenery_type_no_show(self):
        """Test DELETE returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/scenery/types?id=1",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)


class TestSceneryController(DigiScriptTestCase):
    """Test suite for /api/v1/show/stage/scenery endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create a scenery type
            scenery_type = SceneryType(
                show_id=show.id, name="Backdrops", description=""
            )
            session.add(scenery_type)
            session.flush()
            self.scenery_type_id = scenery_type.id

            # Create admin user for RBAC
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            self.user_id = admin.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    # GET tests

    def test_get_scenery_empty(self):
        """Test GET with no scenery returns empty list."""
        response = self.fetch("/api/v1/show/stage/scenery")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("scenery", response_body)
        self.assertEqual([], response_body["scenery"])

    def test_get_scenery_returns_all(self):
        """Test GET returns all scenery for the show."""
        with self._app.get_db().sessionmaker() as session:
            scenery = Scenery(
                show_id=self.show_id,
                scenery_type_id=self.scenery_type_id,
                name="Forest Backdrop",
                description="A woodland scene",
            )
            session.add(scenery)
            session.commit()

        response = self.fetch("/api/v1/show/stage/scenery")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(1, len(response_body["scenery"]))
        self.assertEqual("Forest Backdrop", response_body["scenery"][0]["name"])

    def test_get_scenery_no_show(self):
        """Test GET returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch("/api/v1/show/stage/scenery")
        self.assertEqual(400, response.code)

    # POST tests

    def test_create_scenery_success(self):
        """Test POST creates a new scenery."""
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="POST",
            body=tornado.escape.json_encode(
                {"name": "Castle Wall", "scenery_type_id": self.scenery_type_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("id", response_body)
        self.assertIn("message", response_body)

        # Verify scenery was created
        with self._app.get_db().sessionmaker() as session:
            scenery = session.get(Scenery, response_body["id"])
            self.assertIsNotNone(scenery)
            self.assertEqual("Castle Wall", scenery.name)
            self.assertEqual(self.scenery_type_id, scenery.scenery_type_id)

    def test_create_scenery_with_description(self):
        """Test POST creates a scenery with description."""
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="POST",
            body=tornado.escape.json_encode(
                {
                    "name": "Castle Wall",
                    "scenery_type_id": self.scenery_type_id,
                    "description": "Stone castle wall",
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Verify description was saved
        with self._app.get_db().sessionmaker() as session:
            scenery = session.get(Scenery, response_body["id"])
            self.assertEqual("Stone castle wall", scenery.description)

    def test_create_scenery_missing_name(self):
        """Test POST returns 400 when name is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="POST",
            body=tornado.escape.json_encode({"scenery_type_id": self.scenery_type_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Name missing", response_body["message"])

    def test_create_scenery_missing_scenery_type_id(self):
        """Test POST returns 400 when scenery_type_id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="POST",
            body=tornado.escape.json_encode({"name": "Castle Wall"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Scenery type ID missing", response_body["message"])

    def test_create_scenery_invalid_scenery_type_id(self):
        """Test POST returns 400 for non-integer scenery_type_id."""
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="POST",
            body=tornado.escape.json_encode(
                {"name": "Castle Wall", "scenery_type_id": "invalid"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        # Note: The controller has a typo in the error message
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Scenery prop type ID", response_body["message"])

    def test_create_scenery_scenery_type_not_found(self):
        """Test POST returns 404 for non-existent scenery type."""
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="POST",
            body=tornado.escape.json_encode(
                {"name": "Castle Wall", "scenery_type_id": 99999}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Scenery type not found", response_body["message"])

    def test_create_scenery_scenery_type_wrong_show(self):
        """Test POST returns 400 for scenery type from different show."""
        # Create another show with a scenery type
        with self._app.get_db().sessionmaker() as session:
            other_show = Show(name="Other Show", script_mode=ShowScriptType.FULL)
            session.add(other_show)
            session.flush()

            other_scenery_type = SceneryType(
                show_id=other_show.id, name="Other Type", description=""
            )
            session.add(other_scenery_type)
            session.flush()
            other_scenery_type_id = other_scenery_type.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="POST",
            body=tornado.escape.json_encode(
                {"name": "Castle Wall", "scenery_type_id": other_scenery_type_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid scenery type for show", response_body["message"])

    def test_create_scenery_no_show(self):
        """Test POST returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="POST",
            body=tornado.escape.json_encode(
                {"name": "Castle Wall", "scenery_type_id": self.scenery_type_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    # PATCH tests

    def test_update_scenery_success(self):
        """Test PATCH updates an existing scenery."""
        # Create a scenery first
        with self._app.get_db().sessionmaker() as session:
            scenery = Scenery(
                show_id=self.show_id,
                scenery_type_id=self.scenery_type_id,
                name="Castle Wall",
                description="",
            )
            session.add(scenery)
            session.flush()
            scenery_id = scenery.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="PATCH",
            body=tornado.escape.json_encode(
                {
                    "id": scenery_id,
                    "name": "Stone Wall",
                    "scenery_type_id": self.scenery_type_id,
                    "description": "Updated",
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify update
        with self._app.get_db().sessionmaker() as session:
            scenery = session.get(Scenery, scenery_id)
            self.assertEqual("Stone Wall", scenery.name)
            self.assertEqual("Updated", scenery.description)

    def test_update_scenery_missing_id(self):
        """Test PATCH returns 400 when id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="PATCH",
            body=tornado.escape.json_encode(
                {"name": "Stone Wall", "scenery_type_id": self.scenery_type_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_update_scenery_not_found(self):
        """Test PATCH returns 404 for non-existent scenery."""
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="PATCH",
            body=tornado.escape.json_encode(
                {
                    "id": 99999,
                    "name": "Stone Wall",
                    "scenery_type_id": self.scenery_type_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_update_scenery_missing_name(self):
        """Test PATCH returns 400 when name is missing."""
        # Create a scenery first
        with self._app.get_db().sessionmaker() as session:
            scenery = Scenery(
                show_id=self.show_id,
                scenery_type_id=self.scenery_type_id,
                name="Castle Wall",
                description="",
            )
            session.add(scenery)
            session.flush()
            scenery_id = scenery.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": scenery_id, "scenery_type_id": self.scenery_type_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Name missing", response_body["message"])

    def test_update_scenery_missing_scenery_type_id(self):
        """Test PATCH returns 400 when scenery_type_id is missing."""
        # Create a scenery first
        with self._app.get_db().sessionmaker() as session:
            scenery = Scenery(
                show_id=self.show_id,
                scenery_type_id=self.scenery_type_id,
                name="Castle Wall",
                description="",
            )
            session.add(scenery)
            session.flush()
            scenery_id = scenery.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="PATCH",
            body=tornado.escape.json_encode({"id": scenery_id, "name": "Stone Wall"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Scenery type ID missing", response_body["message"])

    def test_update_scenery_invalid_scenery_type_id(self):
        """Test PATCH returns 400 for non-integer scenery_type_id."""
        # Create a scenery first
        with self._app.get_db().sessionmaker() as session:
            scenery = Scenery(
                show_id=self.show_id,
                scenery_type_id=self.scenery_type_id,
                name="Castle Wall",
                description="",
            )
            session.add(scenery)
            session.flush()
            scenery_id = scenery.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": scenery_id, "name": "Stone Wall", "scenery_type_id": "invalid"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        # Note: The controller has a typo in the error message
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Scenery prop type ID", response_body["message"])

    def test_update_scenery_scenery_type_not_found(self):
        """Test PATCH returns 404 for non-existent scenery type."""
        # Create a scenery first
        with self._app.get_db().sessionmaker() as session:
            scenery = Scenery(
                show_id=self.show_id,
                scenery_type_id=self.scenery_type_id,
                name="Castle Wall",
                description="",
            )
            session.add(scenery)
            session.flush()
            scenery_id = scenery.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": scenery_id, "name": "Stone Wall", "scenery_type_id": 99999}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Scenery type not found", response_body["message"])

    def test_update_scenery_scenery_type_wrong_show(self):
        """Test PATCH returns 400 for scenery type from different show."""
        # Create a scenery first
        with self._app.get_db().sessionmaker() as session:
            scenery = Scenery(
                show_id=self.show_id,
                scenery_type_id=self.scenery_type_id,
                name="Castle Wall",
                description="",
            )
            session.add(scenery)
            session.flush()
            scenery_id = scenery.id

            # Create another show with a scenery type
            other_show = Show(name="Other Show", script_mode=ShowScriptType.FULL)
            session.add(other_show)
            session.flush()

            other_scenery_type = SceneryType(
                show_id=other_show.id, name="Other Type", description=""
            )
            session.add(other_scenery_type)
            session.flush()
            other_scenery_type_id = other_scenery_type.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="PATCH",
            body=tornado.escape.json_encode(
                {
                    "id": scenery_id,
                    "name": "Stone Wall",
                    "scenery_type_id": other_scenery_type_id,
                }
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid scenery type for show", response_body["message"])

    def test_update_scenery_no_show(self):
        """Test PATCH returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": 1, "name": "Stone Wall", "scenery_type_id": self.scenery_type_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    # DELETE tests

    def test_delete_scenery_success(self):
        """Test DELETE removes a scenery."""
        # Create a scenery first
        with self._app.get_db().sessionmaker() as session:
            scenery = Scenery(
                show_id=self.show_id,
                scenery_type_id=self.scenery_type_id,
                name="Castle Wall",
                description="",
            )
            session.add(scenery)
            session.flush()
            scenery_id = scenery.id
            session.commit()

        response = self.fetch(
            f"/api/v1/show/stage/scenery?id={scenery_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify deletion
        with self._app.get_db().sessionmaker() as session:
            scenery = session.get(Scenery, scenery_id)
            self.assertIsNone(scenery)

    def test_delete_scenery_missing_id(self):
        """Test DELETE returns 400 when id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/scenery",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_delete_scenery_invalid_id(self):
        """Test DELETE returns 400 for non-integer ID."""
        response = self.fetch(
            "/api/v1/show/stage/scenery?id=invalid",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid ID", response_body["message"])

    def test_delete_scenery_not_found(self):
        """Test DELETE returns 404 for non-existent scenery."""
        response = self.fetch(
            "/api/v1/show/stage/scenery?id=99999",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_delete_scenery_no_show(self):
        """Test DELETE returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/scenery?id=1",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
