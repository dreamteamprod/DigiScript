import json

from tornado import escape

from models.cue import Cue, CueAssociation, CueType
from models.script import (
    Script,
    ScriptLine,
    ScriptLineRevisionAssociation,
    ScriptRevision,
)
from models.show import Show
from models.user import User

from .test_utils import DigiScriptTestCase


class TestScriptRevisionDeletion(DigiScriptTestCase):

    def setUp(self):
        super().setUp()
        self.create_user_and_login()
        self.create_test_data()

    def create_user_and_login(self):
        """Create a test user and get authentication token"""
        response = self.fetch(
            "/api/v1/auth/create",
            method="POST",
            body=escape.json_encode(
                {
                    "username": "admin",
                    "password": "password",
                    "is_admin": True,
                }
            ),
        )
        self.assertEqual(200, response.code)

        response = self.fetch(
            "/api/v1/auth/login",
            method="POST",
            body=escape.json_encode({"username": "admin", "password": "password"}),
        )
        response_body = escape.json_decode(response.body)
        self.assertEqual(200, response.code)
        self.auth_token = response_body["access_token"]

    def create_test_data(self):
        """Create a show with script revisions, lines, and cues for testing"""
        from models.models import db

        session = db.sessionmaker()

        show = Show(name="Test Show")
        session.add(show)
        session.flush()

        script = Script(show_id=show.id)
        session.add(script)
        session.flush()

        revision1 = ScriptRevision(
            script_id=script.id,
            revision=1,
            description="Initial revision",
            created_at=None,
            edited_at=None,
        )
        session.add(revision1)
        session.flush()

        revision2 = ScriptRevision(
            script_id=script.id,
            revision=2,
            description="Second revision",
            created_at=None,
            edited_at=None,
            previous_revision_id=revision1.id,
        )
        session.add(revision2)
        session.flush()

        script.current_revision = revision2.id

        line1 = ScriptLine(page=1, stage_direction=False)
        line2 = ScriptLine(page=1, stage_direction=True)
        session.add_all([line1, line2])
        session.flush()

        line_assoc1 = ScriptLineRevisionAssociation(
            revision_id=revision2.id, line_id=line1.id, next_line_id=line2.id
        )
        line_assoc2 = ScriptLineRevisionAssociation(
            revision_id=revision2.id, line_id=line2.id, previous_line_id=line1.id
        )
        session.add_all([line_assoc1, line_assoc2])

        cue_type = CueType(
            show_id=show.id, prefix="LX", description="Lighting", colour="#FF0000"
        )
        session.add(cue_type)
        session.flush()

        cue1 = Cue(cue_type_id=cue_type.id, ident="1")
        cue2 = Cue(cue_type_id=cue_type.id, ident="2")
        session.add_all([cue1, cue2])
        session.flush()

        cue_assoc1 = CueAssociation(
            revision_id=revision2.id, line_id=line1.id, cue_id=cue1.id
        )
        cue_assoc2 = CueAssociation(
            revision_id=revision2.id, line_id=line2.id, cue_id=cue2.id
        )
        session.add_all([cue_assoc1, cue_assoc2])

        session.commit()

        self.show_id = show.id
        self.script_id = script.id
        self.revision1_id = revision1.id
        self.revision2_id = revision2.id
        self.line1_id = line1.id
        self.line2_id = line2.id
        self.cue1_id = cue1.id
        self.cue2_id = cue2.id

        session.close()

    def test_delete_script_revision_with_associations(self):
        """Test that deleting a script revision properly removes associated lines and cues"""
        from models.models import db

        session = db.sessionmaker()

        revision = session.query(ScriptRevision).get(self.revision2_id)
        self.assertIsNotNone(revision)

        line_associations = (
            session.query(ScriptLineRevisionAssociation)
            .filter(ScriptLineRevisionAssociation.revision_id == self.revision2_id)
            .all()
        )
        self.assertEqual(len(line_associations), 2)

        cue_associations = (
            session.query(CueAssociation)
            .filter(CueAssociation.revision_id == self.revision2_id)
            .all()
        )
        self.assertEqual(len(cue_associations), 2)
        session.close()

        import asyncio

        asyncio.get_event_loop().run_until_complete(
            self._app.digi_settings.set("current_show", self.show_id)
        )

        response = self.fetch(
            f"/api/v1/show/script/revisions",
            method="DELETE",
            body=escape.json_encode({"rev_id": self.revision2_id}),
            headers={"Authorization": f"Bearer {self.auth_token}"},
            allow_nonstandard_methods=True,
        )

        if response.code == 200:
            from models.models import db

            session = db.sessionmaker()
            revision = session.query(ScriptRevision).get(self.revision2_id)
            self.assertIsNone(revision, "Revision should be deleted")

            line_associations = (
                session.query(ScriptLineRevisionAssociation)
                .filter(ScriptLineRevisionAssociation.revision_id == self.revision2_id)
                .all()
            )
            self.assertEqual(
                len(line_associations), 0, "Line associations should be deleted"
            )

            cue_associations = (
                session.query(CueAssociation)
                .filter(CueAssociation.revision_id == self.revision2_id)
                .all()
            )
            self.assertEqual(
                len(cue_associations), 0, "Cue associations should be deleted"
            )

            line1 = session.query(ScriptLine).get(self.line1_id)
            line2 = session.query(ScriptLine).get(self.line2_id)
            self.assertIsNone(line1, "Line 1 should be deleted")
            self.assertIsNone(line2, "Line 2 should be deleted")

            cue1 = session.query(Cue).get(self.cue1_id)
            cue2 = session.query(Cue).get(self.cue2_id)
            self.assertIsNone(cue1, "Cue 1 should be deleted")
            self.assertIsNone(cue2, "Cue 2 should be deleted")
            session.close()
        else:
            response_body = escape.json_decode(response.body)
            self.fail(
                f"Script revision deletion failed with status {response.code}: {response_body}"
            )
