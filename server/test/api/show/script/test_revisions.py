import tornado.escape
from sqlalchemy import func, select

from models.script import Script, ScriptRevision
from models.show import Show
from test.utils import DigiScriptTestCase


class TestScriptRevisionsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/revisions endpoints."""

    def setUp(self):
        super().setUp()
        # Create base test data
        with self._app.get_db().sessionmaker() as session:
            # Create a test show
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create script
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            # Create first revision
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id

            # Link revision to script
            script.current_revision = revision1.id

            # Create second revision
            revision2 = ScriptRevision(
                script_id=script.id,
                revision=2,
                description="Second",
                previous_revision_id=revision1.id,
            )
            session.add(revision2)
            session.flush()
            self.revision2_id = revision2.id

            session.commit()

        # Set current show
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_revisions(self):
        """Test GET /api/v1/show/script/revisions.

        This tests the query at line 36:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/script/revisions")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(self.revision1_id, response_body["current_revision"])
        self.assertEqual(2, len(response_body["revisions"]))

    def test_get_revisions_no_script(self):
        """Test GET /api/v1/show/script/revisions returns 404 when no script exists."""
        # Create a show with no script
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Empty Show")
            session.add(show2)
            session.commit()
            empty_show_id = show2.id

        self._app.digi_settings.settings["current_show"].set_value(empty_show_id)

        response = self.fetch("/api/v1/show/script/revisions")
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("404 script not found", response_body["message"])


class TestScriptCurrentRevisionController(DigiScriptTestCase):
    """Test suite for /api/v1/show/script/revisions/current endpoints."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_current_revision(self):
        """Test GET /api/v1/show/script/revisions/current.

        This tests the query at line 255:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/script/revisions/current")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(self.revision_id, response_body["current_revision"])

    def test_get_current_revision_no_script(self):
        """Test GET returns 404 when no script exists."""
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Empty Show")
            session.add(show2)
            session.commit()
            empty_show_id = show2.id

        self._app.digi_settings.settings["current_show"].set_value(empty_show_id)

        response = self.fetch("/api/v1/show/script/revisions/current")
        self.assertEqual(404, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("404 script not found", response_body["message"])


class TestScriptRevisionCreate(DigiScriptTestCase):
    """Test POST /api/v1/show/script/revisions endpoint.

    This tests the func.max() query at lines 89-93 in controllers/api/show/script/revisions.py:
    session.scalar(
        select(func.max(ScriptRevision.revision))
        .where(ScriptRevision.script_id == script.id)
    )

    The query is used to determine the next revision number when creating a new revision.
    """

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            from models.user import User

            # Create admin user for authentication
            user = User(username="admin", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            # Create show
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create script
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            # Create initial revision
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id
            script.current_revision = revision1.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_create_revision_uses_max_query(self):
        """Test POST /api/v1/show/script/revisions creates revision with correct number.

        When creating a new revision, the endpoint uses func.max() to find the highest
        existing revision number and increments it. This test verifies that behavior.
        """
        # Create a JWT token for authentication
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Create a new revision - this triggers the max query
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode({"description": "Second revision"}),
            headers={"Authorization": f"Bearer {token}"},
        )

        # Verify the revision was created
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        new_revision_id = response_body["id"]

        # Verify the new revision has the correct number (2)
        with self._app.get_db().sessionmaker() as session:
            new_rev = session.get(ScriptRevision, new_revision_id)
            self.assertEqual(2, new_rev.revision)


class TestScriptRevisionDelete(DigiScriptTestCase):
    """Test DELETE /api/v1/show/script/revisions endpoint.

    This tests the "find revision 1" query at lines 206-213 in controllers/api/show/script/revisions.py:
    session.scalars(
        select(ScriptRevision)
        .where(ScriptRevision.script_id == script.id, ScriptRevision.revision == 1)
    ).one()

    The query is used as a fallback when deleting the current revision and it has no previous_revision_id.
    """

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            from models.user import User

            # Create admin user for authentication
            user = User(username="admin", password="hashed", is_admin=True)
            session.add(user)
            session.flush()
            self.user_id = user.id

            # Create show
            show = Show(name="Test Show")
            session.add(show)
            session.flush()
            self.show_id = show.id

            # Create script
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            # Create revision 1
            revision1 = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision1)
            session.flush()
            self.revision1_id = revision1.id

            # Create revision 2 WITHOUT previous_revision_id (unusual case)
            # This forces the fallback query when we delete it
            revision2 = ScriptRevision(
                script_id=script.id,
                revision=2,
                description="Second",
                previous_revision_id=None,  # No link to previous!
            )
            session.add(revision2)
            session.flush()
            self.revision2_id = revision2.id

            # Make revision 2 current
            script.current_revision = revision2.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_delete_revision_uses_find_first_query(self):
        """Test DELETE /api/v1/show/script/revisions falls back to revision 1.

        When deleting the current revision that has no previous_revision_id,
        the endpoint uses a query to find revision 1 as a fallback.
        """
        # Create a JWT token for authentication
        token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

        # Delete revision 2 - this triggers the "find revision 1" fallback query
        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="DELETE",
            body=tornado.escape.json_encode({"rev_id": self.revision2_id}),
            headers={"Authorization": f"Bearer {token}"},
            allow_nonstandard_methods=True,
        )

        # Verify the deletion succeeded
        self.assertEqual(200, response.code)

        # Verify the script now points to revision 1 (the fallback)
        with self._app.get_db().sessionmaker() as session:
            script = session.get(Script, self.script_id)
            self.assertEqual(self.revision1_id, script.current_revision)
