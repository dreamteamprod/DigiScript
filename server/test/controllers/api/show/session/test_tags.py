"""Tests for SessionTag CRUD API controller."""

from sqlalchemy import insert, select
from tornado import escape

from models.session import SessionTag, ShowSession, session_tag_association_table
from models.show import Show, ShowScriptType
from models.user import User
from test.conftest import DigiScriptTestCase


class TestSessionTagsController(DigiScriptTestCase):
    """Test SessionTagsController CRUD operations."""

    def setUp(self):
        """Set up test environment with show, admin user, and JWT token."""
        super().setUp()
        # Create show
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create admin user
            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            self.user_id = admin.id
            session.commit()

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

        # Create JWT token
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def create_tag(self, tag_name, colour="#FF0000"):
        """Helper to create a tag in the database."""
        with self._app.get_db().sessionmaker() as session:
            tag = SessionTag(show_id=self.show_id, tag=tag_name, colour=colour)
            session.add(tag)
            session.flush()
            tag_id = tag.id
            session.commit()
        return tag_id

    # ===========================
    # GET Tests (List Tags)
    # ===========================

    def test_get_tags_empty(self):
        """Test GET /api/v1/show/session/tags with no tags."""
        response = self.fetch("/api/v1/show/session/tags")
        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("tags", response_body)
        self.assertEqual([], response_body["tags"])

    def test_get_tags_with_data(self):
        """Test GET /api/v1/show/session/tags with existing tags."""
        # Create test tags
        self.create_tag("Tech", "#FF5733")
        self.create_tag("Dress", "#3498DB")
        self.create_tag("Opening Night", "#2ECC71")

        response = self.fetch("/api/v1/show/session/tags")
        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertEqual(3, len(response_body["tags"]))

        tag_names = [t["tag"] for t in response_body["tags"]]
        self.assertIn("Tech", tag_names)
        self.assertIn("Dress", tag_names)
        self.assertIn("Opening Night", tag_names)

        # Verify fields are serialized
        for tag in response_body["tags"]:
            self.assertIn("id", tag)
            self.assertIn("tag", tag)
            self.assertIn("colour", tag)
            self.assertIn("show_id", tag)

    # ===========================
    # POST Tests (Create Tag)
    # ===========================

    def test_post_tag_success(self):
        """Test POST /api/v1/show/session/tags with valid data."""
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="POST",
            body=escape.json_encode({"tag": "Tech", "colour": "#FF5733"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("id", response_body)
        self.assertIn("Successfully added session tag", response_body["message"])

        # Verify tag was created in database
        tag_id = response_body["id"]
        with self._app.get_db().sessionmaker() as session:
            tag = session.scalars(
                select(SessionTag).where(SessionTag.id == tag_id)
            ).first()
            self.assertIsNotNone(tag)
            self.assertEqual("Tech", tag.tag)
            self.assertEqual("#FF5733", tag.colour)
            self.assertEqual(self.show_id, tag.show_id)

    def test_post_tag_missing_tag_name(self):
        """Test POST /api/v1/show/session/tags without tag name."""
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="POST",
            body=escape.json_encode({"colour": "#FF5733"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("Tag name missing", response_body["message"])

    def test_post_tag_missing_colour(self):
        """Test POST /api/v1/show/session/tags without colour."""
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="POST",
            body=escape.json_encode({"tag": "Tech"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("Colour missing", response_body["message"])

    def test_post_tag_duplicate_case_insensitive(self):
        """Test POST /api/v1/show/session/tags with duplicate name (case-insensitive)."""
        # Create first tag
        self.create_tag("Tech", "#FF5733")

        # Try to create tag with different case
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="POST",
            body=escape.json_encode({"tag": "tech", "colour": "#000000"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn(
            "Tag name already exists (case-insensitive)", response_body["message"]
        )

    def test_post_tag_duplicate_case_variations(self):
        """Test POST /api/v1/show/session/tags with multiple case variations."""
        # Create first tag
        self.create_tag("Matinee", "#FF5733")

        # Try uppercase
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="POST",
            body=escape.json_encode({"tag": "MATINEE", "colour": "#000000"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

        # Try lowercase
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="POST",
            body=escape.json_encode({"tag": "matinee", "colour": "#000000"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

        # Try mixed case
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="POST",
            body=escape.json_encode({"tag": "MaTiNeE", "colour": "#000000"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    # ===========================
    # PATCH Tests (Update Tag)
    # ===========================

    def test_patch_tag_success(self):
        """Test PATCH /api/v1/show/session/tags with valid data."""
        tag_id = self.create_tag("Tech", "#FF5733")

        response = self.fetch(
            "/api/v1/show/session/tags",
            method="PATCH",
            body=escape.json_encode(
                {"id": tag_id, "tag": "Tech Rehearsal", "colour": "#2ECC71"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("Successfully updated session tag", response_body["message"])

        # Verify updates persisted
        with self._app.get_db().sessionmaker() as session:
            tag = session.scalars(
                select(SessionTag).where(SessionTag.id == tag_id)
            ).first()
            self.assertIsNotNone(tag)
            self.assertEqual("Tech Rehearsal", tag.tag)
            self.assertEqual("#2ECC71", tag.colour)

    def test_patch_tag_missing_id(self):
        """Test PATCH /api/v1/show/session/tags without ID."""
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="PATCH",
            body=escape.json_encode({"tag": "Tech", "colour": "#FF5733"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_patch_tag_missing_tag_name(self):
        """Test PATCH /api/v1/show/session/tags without tag name."""
        tag_id = self.create_tag("Tech", "#FF5733")

        response = self.fetch(
            "/api/v1/show/session/tags",
            method="PATCH",
            body=escape.json_encode({"id": tag_id, "colour": "#2ECC71"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("Tag name missing", response_body["message"])

    def test_patch_tag_missing_colour(self):
        """Test PATCH /api/v1/show/session/tags without colour."""
        tag_id = self.create_tag("Tech", "#FF5733")

        response = self.fetch(
            "/api/v1/show/session/tags",
            method="PATCH",
            body=escape.json_encode({"id": tag_id, "tag": "Tech Rehearsal"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("Colour missing", response_body["message"])

    def test_patch_tag_not_found(self):
        """Test PATCH /api/v1/show/session/tags with non-existent ID."""
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="PATCH",
            body=escape.json_encode({"id": 999999, "tag": "Tech", "colour": "#FF5733"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("404 tag not found", response_body["message"])

    def test_patch_tag_duplicate_case_insensitive(self):
        """Test PATCH /api/v1/show/session/tags with duplicate name (case-insensitive)."""
        # Create two tags
        tag_id_1 = self.create_tag("Tech", "#FF5733")
        self.create_tag("Dress", "#3498DB")

        # Try to update second tag to match first (different case)
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="PATCH",
            body=escape.json_encode(
                {"id": tag_id_1, "tag": "dress", "colour": "#000000"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn(
            "Tag name already exists (case-insensitive)", response_body["message"]
        )

    def test_patch_tag_same_name_allowed(self):
        """Test PATCH /api/v1/show/session/tags with same name (no duplicate error)."""
        tag_id = self.create_tag("Tech", "#FF5733")

        # Update with same name but different colour
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="PATCH",
            body=escape.json_encode({"id": tag_id, "tag": "Tech", "colour": "#2ECC71"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("Successfully updated session tag", response_body["message"])

    def test_patch_tag_case_change_only(self):
        """Test PATCH /api/v1/show/session/tags with only case change."""
        tag_id = self.create_tag("Tech", "#FF5733")

        # Update to uppercase
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="PATCH",
            body=escape.json_encode({"id": tag_id, "tag": "TECH", "colour": "#FF5733"}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify database has uppercase version
        with self._app.get_db().sessionmaker() as session:
            tag = session.scalars(
                select(SessionTag).where(SessionTag.id == tag_id)
            ).first()
            self.assertEqual("TECH", tag.tag)

    # ===========================
    # DELETE Tests (Remove Tag)
    # ===========================

    def test_delete_tag_success(self):
        """Test DELETE /api/v1/show/session/tags with valid ID."""
        tag_id = self.create_tag("Tech", "#FF5733")

        response = self.fetch(
            f"/api/v1/show/session/tags?id={tag_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("Successfully deleted session tag", response_body["message"])

        # Verify tag no longer exists
        with self._app.get_db().sessionmaker() as session:
            tag = session.scalars(
                select(SessionTag).where(SessionTag.id == tag_id)
            ).first()
            self.assertIsNone(tag)

    def test_delete_tag_missing_id(self):
        """Test DELETE /api/v1/show/session/tags without ID."""
        response = self.fetch(
            "/api/v1/show/session/tags",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("ID missing", response_body["message"])

    def test_delete_tag_not_found(self):
        """Test DELETE /api/v1/show/session/tags with non-existent ID."""
        response = self.fetch(
            "/api/v1/show/session/tags?id=999999",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("404 tag not found", response_body["message"])

    def test_delete_tag_cascade_associations(self):
        """Test DELETE /api/v1/show/session/tags with associations."""
        tag_id = self.create_tag("Tech", "#FF5733")

        # Create a ShowSession and associate the tag
        with self._app.get_db().sessionmaker() as session:
            show_session = ShowSession(show_id=self.show_id)
            session.add(show_session)
            session.flush()
            session_id = show_session.id

            # Create association using insert on the Table
            session.execute(
                insert(session_tag_association_table).values(
                    session_id=session_id, tag_id=tag_id
                )
            )
            session.commit()

        # Verify association exists
        with self._app.get_db().sessionmaker() as session:
            assoc = session.execute(
                select(session_tag_association_table).where(
                    session_tag_association_table.c.tag_id == tag_id
                )
            ).first()
            self.assertIsNotNone(assoc)

        # Delete tag
        response = self.fetch(
            f"/api/v1/show/session/tags?id={tag_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify tag deleted
        with self._app.get_db().sessionmaker() as session:
            tag = session.scalars(
                select(SessionTag).where(SessionTag.id == tag_id)
            ).first()
            self.assertIsNone(tag)

            # Verify association also deleted (cascade)
            assoc = session.execute(
                select(session_tag_association_table).where(
                    session_tag_association_table.c.tag_id == tag_id
                )
            ).first()
            self.assertIsNone(assoc)

            # Verify ShowSession still exists
            show_session = session.scalars(
                select(ShowSession).where(ShowSession.id == session_id)
            ).first()
            self.assertIsNotNone(show_session)
