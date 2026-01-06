"""Tests for Session Tag Assignment API controller."""

from sqlalchemy import select
from tornado import escape

from models.session import SessionTag, ShowSession
from models.show import Show, ShowScriptType
from models.user import User
from test.conftest import DigiScriptTestCase


class TestSessionTagAssignmentController(DigiScriptTestCase):
    """Test SessionTagAssignmentController."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            admin = User(username="admin", is_admin=True, password="test")
            session.add(admin)
            session.flush()
            self.user_id = admin.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def create_tag(self, tag_name, colour="#FF0000"):
        """Helper to create a tag."""
        with self._app.get_db().sessionmaker() as session:
            tag = SessionTag(show_id=self.show_id, tag=tag_name, colour=colour)
            session.add(tag)
            session.flush()
            tag_id = tag.id
            session.commit()
        return tag_id

    def create_session(self):
        """Helper to create a ShowSession."""
        with self._app.get_db().sessionmaker() as session:
            show_session = ShowSession(show_id=self.show_id)
            session.add(show_session)
            session.flush()
            session_id = show_session.id
            session.commit()
        return session_id

    # ========== SUCCESS CASES ==========

    def test_patch_session_tags_single_tag(self):
        """Test assigning single tag to session."""
        session_id = self.create_session()
        tag_id = self.create_tag("Tech", "#FF5733")

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode({"session_id": session_id, "tag_ids": [tag_id]}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        # Verify assignment
        with self._app.get_db().sessionmaker() as session:
            show_session = session.get(ShowSession, session_id)
            self.assertEqual(1, len(show_session.tags))
            self.assertEqual(tag_id, show_session.tags[0].id)

    def test_patch_session_tags_multiple_tags(self):
        """Test assigning multiple tags to session."""
        session_id = self.create_session()
        tag1 = self.create_tag("Tech", "#FF5733")
        tag2 = self.create_tag("Dress", "#3498DB")
        tag3 = self.create_tag("Opening", "#2ECC71")

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode(
                {"session_id": session_id, "tag_ids": [tag1, tag2, tag3]}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            show_session = session.get(ShowSession, session_id)
            self.assertEqual(3, len(show_session.tags))
            tag_ids = {tag.id for tag in show_session.tags}
            self.assertEqual({tag1, tag2, tag3}, tag_ids)

    def test_patch_session_tags_replace_existing(self):
        """Test replacing existing tags."""
        session_id = self.create_session()
        tag1 = self.create_tag("Tech", "#FF5733")
        tag2 = self.create_tag("Dress", "#3498DB")
        tag3 = self.create_tag("Opening", "#2ECC71")

        # Assign tag1 and tag2
        self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode(
                {"session_id": session_id, "tag_ids": [tag1, tag2]}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        # Replace with tag2 and tag3
        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode(
                {"session_id": session_id, "tag_ids": [tag2, tag3]}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            show_session = session.get(ShowSession, session_id)
            self.assertEqual(2, len(show_session.tags))
            tag_ids = {tag.id for tag in show_session.tags}
            self.assertEqual({tag2, tag3}, tag_ids)

    def test_patch_session_tags_empty_list(self):
        """Test removing all tags with empty list."""
        session_id = self.create_session()
        tag_id = self.create_tag("Tech", "#FF5733")

        # Assign tag
        self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode({"session_id": session_id, "tag_ids": [tag_id]}),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        # Remove all tags
        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode({"session_id": session_id, "tag_ids": []}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            show_session = session.get(ShowSession, session_id)
            self.assertEqual(0, len(show_session.tags))

    # ========== VALIDATION CASES ==========

    def test_patch_session_tags_missing_session_id(self):
        """Test PATCH without session_id field."""
        tag_id = self.create_tag("Tech", "#FF5733")

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode({"tag_ids": [tag_id]}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("session_id missing", response_body["message"])

    def test_patch_session_tags_invalid_session_id_type(self):
        """Test PATCH with session_id not an integer."""
        tag_id = self.create_tag("Tech", "#FF5733")

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode({"session_id": "not an int", "tag_ids": [tag_id]}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("session_id must be an integer", response_body["message"])

    def test_patch_session_tags_missing_tag_ids(self):
        """Test PATCH without tag_ids field."""
        session_id = self.create_session()

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode({"session_id": session_id}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("tag_ids missing", response_body["message"])

    def test_patch_session_tags_invalid_tag_ids_type(self):
        """Test PATCH with tag_ids not a list."""
        session_id = self.create_session()

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode(
                {"session_id": session_id, "tag_ids": "not a list"}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("tag_ids must be a list", response_body["message"])

    def test_patch_session_tags_invalid_tag_id(self):
        """Test PATCH with non-existent tag ID."""
        session_id = self.create_session()

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode({"session_id": session_id, "tag_ids": [999999]}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("One or more tag IDs are invalid", response_body["message"])

    def test_patch_session_tags_session_not_found(self):
        """Test PATCH with non-existent session ID."""
        tag_id = self.create_tag("Tech", "#FF5733")

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode({"session_id": 999999, "tag_ids": [tag_id]}),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(404, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("404 session not found", response_body["message"])

    def test_patch_session_tags_tag_from_different_show(self):
        """Test PATCH with tag from different show."""
        session_id = self.create_session()

        # Create second show with tag
        with self._app.get_db().sessionmaker() as session:
            other_show = Show(name="Other Show", script_mode=ShowScriptType.FULL)
            session.add(other_show)
            session.flush()

            other_tag = SessionTag(
                show_id=other_show.id, tag="Other Tag", colour="#000000"
            )
            session.add(other_tag)
            session.flush()
            other_tag_id = other_tag.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode(
                {"session_id": session_id, "tag_ids": [other_tag_id]}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("One or more tag IDs are invalid", response_body["message"])

    def test_patch_session_tags_session_from_different_show(self):
        """Test PATCH with session from different show."""
        tag_id = self.create_tag("Tech", "#FF5733")

        # Create second show with session
        with self._app.get_db().sessionmaker() as session:
            other_show = Show(name="Other Show", script_mode=ShowScriptType.FULL)
            session.add(other_show)
            session.flush()

            other_session = ShowSession(show_id=other_show.id)
            session.add(other_session)
            session.flush()
            other_session_id = other_session.id
            session.commit()

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode(
                {"session_id": other_session_id, "tag_ids": [tag_id]}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(403, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn(
            "Session does not belong to current show", response_body["message"]
        )

    # ========== RBAC CASES ==========

    def test_patch_session_tags_requires_authentication(self):
        """Test PATCH requires authentication."""
        session_id = self.create_session()
        tag_id = self.create_tag("Tech", "#FF5733")

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode({"session_id": session_id, "tag_ids": [tag_id]}),
        )
        self.assertEqual(401, response.code)

    def test_patch_session_tags_partial_tag_list_invalid(self):
        """Test PATCH with some valid and some invalid tag IDs."""
        session_id = self.create_session()
        tag1 = self.create_tag("Tech", "#FF5733")
        invalid_tag_id = 999999

        response = self.fetch(
            "/api/v1/show/sessions/assign-tags",
            method="PATCH",
            body=escape.json_encode(
                {"session_id": session_id, "tag_ids": [tag1, invalid_tag_id]}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)
        response_body = escape.json_decode(response.body)
        self.assertIn("One or more tag IDs are invalid", response_body["message"])

        # Verify no tags were assigned (atomic operation)
        with self._app.get_db().sessionmaker() as session:
            show_session = session.get(ShowSession, session_id)
            self.assertEqual(0, len(show_session.tags))
