import tornado.escape

from models.show import Show, ShowScriptType
from models.stage import Crew
from models.user import User
from test.conftest import DigiScriptTestCase


class TestCrewController(DigiScriptTestCase):
    """Test suite for /api/v1/show/stage/crew endpoint."""

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

    def test_get_crew_empty(self):
        """Test GET with no crew returns empty list."""
        response = self.fetch("/api/v1/show/stage/crew")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("crew", response_body)
        self.assertEqual([], response_body["crew"])

    def test_get_crew_returns_all(self):
        """Test GET returns all crew members for the show."""
        with self._app.get_db().sessionmaker() as session:
            crew_member = Crew(show_id=self.show_id, first_name="John", last_name="Doe")
            session.add(crew_member)
            session.commit()

        response = self.fetch("/api/v1/show/stage/crew")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(1, len(response_body["crew"]))
        self.assertEqual("John", response_body["crew"][0]["first_name"])
        self.assertEqual("Doe", response_body["crew"][0]["last_name"])

    def test_get_crew_no_show(self):
        """Test GET returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch("/api/v1/show/stage/crew")
        self.assertEqual(400, response.code)

    # POST tests

    def test_create_crew_success(self):
        """Test POST creates a new crew member."""
        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="POST",
            body=tornado.escape.json_encode({"firstName": "Jane", "lastName": "Smith"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("id", response_body)
        self.assertIn("message", response_body)

        # Verify crew member was created
        with self._app.get_db().sessionmaker() as session:
            crew = session.get(Crew, response_body["id"])
            self.assertIsNotNone(crew)
            self.assertEqual("Jane", crew.first_name)
            self.assertEqual("Smith", crew.last_name)

    def test_create_crew_missing_first_name(self):
        """Test POST returns 400 when firstName is missing."""
        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="POST",
            body=tornado.escape.json_encode({"lastName": "Smith"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("First name missing", response_body["message"])

    def test_create_crew_missing_last_name(self):
        """Test POST returns 400 when lastName is missing."""
        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="POST",
            body=tornado.escape.json_encode({"firstName": "Jane"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Last name missing", response_body["message"])

    def test_create_crew_no_show(self):
        """Test POST returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="POST",
            body=tornado.escape.json_encode({"firstName": "Jane", "lastName": "Smith"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    # PATCH tests

    def test_update_crew_success(self):
        """Test PATCH updates an existing crew member."""
        # Create a crew member first
        with self._app.get_db().sessionmaker() as session:
            crew_member = Crew(show_id=self.show_id, first_name="John", last_name="Doe")
            session.add(crew_member)
            session.flush()
            crew_id = crew_member.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": crew_id, "firstName": "Jane", "lastName": "Smith"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify update
        with self._app.get_db().sessionmaker() as session:
            crew = session.get(Crew, crew_id)
            self.assertEqual("Jane", crew.first_name)
            self.assertEqual("Smith", crew.last_name)

    def test_update_crew_missing_id(self):
        """Test PATCH returns 400 when id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="PATCH",
            body=tornado.escape.json_encode({"firstName": "Jane", "lastName": "Smith"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_update_crew_not_found(self):
        """Test PATCH returns 404 for non-existent crew member."""
        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": 99999, "firstName": "Jane", "lastName": "Smith"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_update_crew_missing_first_name(self):
        """Test PATCH returns 400 when firstName is missing."""
        # Create a crew member first
        with self._app.get_db().sessionmaker() as session:
            crew_member = Crew(show_id=self.show_id, first_name="John", last_name="Doe")
            session.add(crew_member)
            session.flush()
            crew_id = crew_member.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="PATCH",
            body=tornado.escape.json_encode({"id": crew_id, "lastName": "Smith"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("First name missing", response_body["message"])

    def test_update_crew_missing_last_name(self):
        """Test PATCH returns 400 when lastName is missing."""
        # Create a crew member first
        with self._app.get_db().sessionmaker() as session:
            crew_member = Crew(show_id=self.show_id, first_name="John", last_name="Doe")
            session.add(crew_member)
            session.flush()
            crew_id = crew_member.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="PATCH",
            body=tornado.escape.json_encode({"id": crew_id, "firstName": "Jane"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Last name missing", response_body["message"])

    def test_update_crew_no_show(self):
        """Test PATCH returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="PATCH",
            body=tornado.escape.json_encode(
                {"id": 1, "firstName": "Jane", "lastName": "Smith"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    # DELETE tests

    def test_delete_crew_success(self):
        """Test DELETE removes a crew member."""
        # Create a crew member first
        with self._app.get_db().sessionmaker() as session:
            crew_member = Crew(show_id=self.show_id, first_name="John", last_name="Doe")
            session.add(crew_member)
            session.flush()
            crew_id = crew_member.id
            session.commit()

        response = self.fetch(
            f"/api/v1/show/stage/crew?id={crew_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify deletion
        with self._app.get_db().sessionmaker() as session:
            crew = session.get(Crew, crew_id)
            self.assertIsNone(crew)

    def test_delete_crew_missing_id(self):
        """Test DELETE returns 400 when id is missing."""
        response = self.fetch(
            "/api/v1/show/stage/crew",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_delete_crew_not_found(self):
        """Test DELETE returns 404 for non-existent crew member."""
        response = self.fetch(
            "/api/v1/show/stage/crew?id=99999",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)

    def test_delete_crew_invalid_id(self):
        """Test DELETE returns 400 when id is not a valid integer."""
        response = self.fetch(
            "/api/v1/show/stage/crew?id=not-a-number",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("Invalid ID", response_body["message"])

    def test_delete_crew_no_show(self):
        """Test DELETE returns 400 when no show is loaded."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch(
            "/api/v1/show/stage/crew?id=1",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
