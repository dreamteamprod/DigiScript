import tornado.escape

from models.show import Act, Scene, Show, ShowScriptType
from models.stage import Props, PropsAllocation, PropType
from models.user import User
from test.conftest import DigiScriptTestCase


class TestPropsAllocationController(DigiScriptTestCase):
    """Test suite for /api/v1/show/stage/props/allocations endpoint."""

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

            # Create a prop type and prop
            prop_type = PropType(show_id=show.id, name="Hand Props", description="")
            session.add(prop_type)
            session.flush()
            self.prop_type_id = prop_type.id

            prop = Props(
                show_id=show.id,
                prop_type_id=prop_type.id,
                name="Sword",
                description="Test prop",
            )
            session.add(prop)
            session.flush()
            self.prop_id = prop.id

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
        response = self.fetch("/api/v1/show/stage/props/allocations")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("allocations", response_body)
        self.assertEqual([], response_body["allocations"])

    def test_get_allocations_returns_all(self):
        """Test GET returns all allocations for the show."""
        # Create an allocation
        with self._app.get_db().sessionmaker() as session:
            allocation = PropsAllocation(props_id=self.prop_id, scene_id=self.scene_id)
            session.add(allocation)
            session.commit()

        response = self.fetch("/api/v1/show/stage/props/allocations")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(1, len(response_body["allocations"]))
        self.assertEqual(self.prop_id, response_body["allocations"][0]["props_id"])
        self.assertEqual(self.scene_id, response_body["allocations"][0]["scene_id"])

    def test_get_allocations_no_show(self):
        """Test GET returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch("/api/v1/show/stage/props/allocations")
        self.assertEqual(400, response.code)

    def test_create_allocation_success(self):
        """Test POST creates a new allocation."""
        response = self.fetch(
            "/api/v1/show/stage/props/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"props_id": self.prop_id, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("id", response_body)
        self.assertIn("message", response_body)

        # Verify allocation was created
        with self._app.get_db().sessionmaker() as session:
            allocation = session.get(PropsAllocation, response_body["id"])
            self.assertIsNotNone(allocation)
            self.assertEqual(self.prop_id, allocation.props_id)
            self.assertEqual(self.scene_id, allocation.scene_id)

    def test_create_allocation_duplicate(self):
        """Test POST returns 400 for duplicate allocation."""
        # Create initial allocation
        with self._app.get_db().sessionmaker() as session:
            allocation = PropsAllocation(props_id=self.prop_id, scene_id=self.scene_id)
            session.add(allocation)
            session.commit()

        # Try to create duplicate
        response = self.fetch(
            "/api/v1/show/stage/props/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"props_id": self.prop_id, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("already exists", response_body["message"])

    def test_create_allocation_invalid_props_id(self):
        """Test POST returns 404 for non-existent prop."""
        response = self.fetch(
            "/api/v1/show/stage/props/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"props_id": 99999, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_create_allocation_invalid_scene_id(self):
        """Test POST returns 404 for non-existent scene."""
        response = self.fetch(
            "/api/v1/show/stage/props/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"props_id": self.prop_id, "scene_id": 99999}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_create_allocation_prop_wrong_show(self):
        """Test POST returns 404 for prop from different show."""
        # Create another show with a prop
        with self._app.get_db().sessionmaker() as session:
            other_show = Show(name="Other Show", script_mode=ShowScriptType.FULL)
            session.add(other_show)
            session.flush()

            other_prop_type = PropType(
                show_id=other_show.id, name="Other Type", description=""
            )
            session.add(other_prop_type)
            session.flush()

            other_prop = Props(
                show_id=other_show.id,
                prop_type_id=other_prop_type.id,
                name="Other Prop",
                description="",
            )
            session.add(other_prop)
            session.flush()
            other_prop_id = other_prop.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/props/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"props_id": other_prop_id, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_create_allocation_missing_props_id(self):
        """Test POST returns 400 when props_id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/props/allocations",
            method="POST",
            body=tornado.escape.json_encode({"scene_id": self.scene_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("props_id missing", response_body["message"])

    def test_create_allocation_missing_scene_id(self):
        """Test POST returns 400 when scene_id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/props/allocations",
            method="POST",
            body=tornado.escape.json_encode({"props_id": self.prop_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("scene_id missing", response_body["message"])

    def test_create_allocation_no_show(self):
        """Test POST returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/props/allocations",
            method="POST",
            body=tornado.escape.json_encode(
                {"props_id": self.prop_id, "scene_id": self.scene_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    def test_delete_allocation_success(self):
        """Test DELETE removes an allocation."""
        # Create an allocation
        with self._app.get_db().sessionmaker() as session:
            allocation = PropsAllocation(props_id=self.prop_id, scene_id=self.scene_id)
            session.add(allocation)
            session.flush()
            allocation_id = allocation.id
            session.commit()

        response = self.fetch(
            f"/api/v1/show/stage/props/allocations?id={allocation_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify allocation was deleted
        with self._app.get_db().sessionmaker() as session:
            allocation = session.get(PropsAllocation, allocation_id)
            self.assertIsNone(allocation)

    def test_delete_allocation_not_found(self):
        """Test DELETE returns 404 for non-existent allocation."""
        response = self.fetch(
            "/api/v1/show/stage/props/allocations?id=99999",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_delete_allocation_missing_id(self):
        """Test DELETE returns 400 when ID is missing."""
        response = self.fetch(
            "/api/v1/show/stage/props/allocations",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_delete_allocation_invalid_id(self):
        """Test DELETE returns 400 for non-integer ID."""
        response = self.fetch(
            "/api/v1/show/stage/props/allocations?id=invalid",
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
            "/api/v1/show/stage/props/allocations?id=1",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
