import tornado.escape
from sqlalchemy import select

from models.cue import Cue, CueAssociation, CueGroup, CueType
from models.script import (
    Script,
    ScriptLine,
    ScriptLineRevisionAssociation,
    ScriptLineType,
    ScriptRevision,
)
from models.session import ShowSession
from models.show import Act, Scene, Show, ShowScriptType
from models.user import User
from rbac.role import Role
from test.conftest import DigiScriptTestCase


class TestCueController(DigiScriptTestCase):
    """Test suite for /api/v1/show/cues endpoint."""

    def setUp(self):
        super().setUp()
        # Create a test show with script
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_cues(self):
        """Test GET /api/v1/show/cues.

        This tests two queries in cues.py:
        - Line 176-177: Script lookup
          session.scalars(select(Script).where(Script.show_id == show.id)).first()
        - Line 190-193: CueAssociation filter
          session.scalars(select(CueAssociation).where(...)).all()
        """
        response = self.fetch("/api/v1/show/cues")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("cues", response_body)

    def test_get_cues_no_script(self):
        """Test GET returns error when no script exists."""
        # Create a show without a script
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Show 2", script_mode=ShowScriptType.FULL)
            session.add(show2)
            session.flush()
            show2_id = show2.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show2_id)

        response = self.fetch("/api/v1/show/cues")
        # Should get an error because there's no script
        self.assertNotEqual(200, response.code)


class TestCueStatsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/cues/stats endpoint."""

    def setUp(self):
        super().setUp()
        # Create a test show with script
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()

            script.current_revision = revision.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_get_cue_stats(self):
        """Test GET /api/v1/show/cues/stats.

        This tests the query at line 455-456 in cues.py:
        session.scalars(select(Script).where(Script.show_id == show.id)).first()
        """
        response = self.fetch("/api/v1/show/cues/stats")
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertIn("cue_counts", response_body)


class TestSpacingLineCueRestriction(DigiScriptTestCase):
    """Test suite for spacing line cue restriction."""

    def setUp(self):
        super().setUp()
        # Create comprehensive test data
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id
            script.current_revision = revision.id

            # Create act and scene for lines
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()
            self.act_id = act.id

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            self.scene_id = scene.id

            # Create a SPACING line
            spacing_line = ScriptLine(
                act_id=act.id,
                scene_id=scene.id,
                page=1,
                line_type=ScriptLineType.SPACING,
            )
            session.add(spacing_line)
            session.flush()
            self.spacing_line_id = spacing_line.id

            # Add line to revision
            assoc = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=spacing_line.id
            )
            session.add(assoc)

            # Create a regular DIALOGUE line for comparison
            dialogue_line = ScriptLine(
                act_id=act.id,
                scene_id=scene.id,
                page=1,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(dialogue_line)
            session.flush()
            self.dialogue_line_id = dialogue_line.id

            # Add dialogue line to revision
            assoc2 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=dialogue_line.id
            )
            session.add(assoc2)

            # Create cue type
            cue_type = CueType(
                show_id=show.id,
                prefix="LX",
                description="Lighting",
                colour="#ff0000",
            )
            session.add(cue_type)
            session.flush()
            self.cue_type_id = cue_type.id

            # Create admin user for RBAC
            test_credential = "test"
            admin = User(username="admin", is_admin=True, password=test_credential)
            session.add(admin)
            session.flush()
            self.user_id = admin.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def test_post_cue_rejects_spacing_line(self):
        """
        Test adding a cue to a SPACING line returns 400.
        """
        cue_data = {
            "cueType": self.cue_type_id,
            "ident": "LX 1",
            "lineId": self.spacing_line_id,
        }

        response = self.fetch(
            "/api/v1/show/cues",
            method="POST",
            body=tornado.escape.json_encode(cue_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(
            "Cannot add cues to spacing lines",
            response_body["message"],
            "Should reject cue on SPACING line with specific error message",
        )

        # Verify no cue was created
        with self._app.get_db().sessionmaker() as session:
            cue_assocs = session.scalars(select(CueAssociation)).all()
            self.assertEqual(
                0,
                len(cue_assocs),
                "No CueAssociation should be created for SPACING line",
            )

    def test_post_cue_allows_dialogue_line(self):
        """
        Test adding a cue to a DIALOGUE line succeeds (regression test).

        Verifies that the SPACING restriction doesn't affect other line types.
        """
        cue_data = {
            "cueType": self.cue_type_id,
            "ident": "LX 1",
            "lineId": self.dialogue_line_id,
        }

        response = self.fetch(
            "/api/v1/show/cues",
            method="POST",
            body=tornado.escape.json_encode(cue_data),
            headers={"Authorization": f"Bearer {self.token}"},
        )

        self.assertEqual(200, response.code, "DIALOGUE line should accept cues")

        # Verify cue was created
        with self._app.get_db().sessionmaker() as session:
            cue_assocs = session.scalars(select(CueAssociation)).all()
            self.assertEqual(
                1,
                len(cue_assocs),
                "CueAssociation should be created for DIALOGUE line",
            )
            self.assertEqual(self.dialogue_line_id, cue_assocs[0].line_id)


class TestCueSearchController(DigiScriptTestCase):
    """Test suite for /api/v1/show/cues/search endpoint."""

    def setUp(self):
        super().setUp()
        # Create comprehensive test data for search functionality
        with self._app.get_db().sessionmaker() as session:
            # 1. Create Show
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            # 2. Create Script with current revision
            script = Script(show_id=show.id)
            session.add(script)
            session.flush()
            self.script_id = script.id

            revision = ScriptRevision(
                script_id=script.id, revision=1, description="Initial"
            )
            session.add(revision)
            session.flush()
            self.revision_id = revision.id
            script.current_revision = revision.id

            # 3. Create Act and Scene for script lines
            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()
            self.act_id = act.id

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            self.scene_id = scene.id

            # 4. Create multiple CueTypes for filtering tests
            cue_type_lighting = CueType(
                show_id=show.id,
                prefix="LX",
                description="Lighting",
                colour="#FF0000",
            )
            session.add(cue_type_lighting)
            session.flush()
            self.cue_type_lighting_id = cue_type_lighting.id

            cue_type_sound = CueType(
                show_id=show.id,
                prefix="SQ",
                description="Sound",
                colour="#00FF00",
            )
            session.add(cue_type_sound)
            session.flush()
            self.cue_type_sound_id = cue_type_sound.id

            # Empty cue type for testing no cues scenario
            cue_type_empty = CueType(
                show_id=show.id,
                prefix="VD",
                description="Video",
                colour="#0000FF",
            )
            session.add(cue_type_empty)
            session.flush()
            self.cue_type_empty_id = cue_type_empty.id

            # 5. Create script lines on different pages
            lines = []
            for page_num in range(1, 4):
                for i in range(4):
                    line = ScriptLine(
                        act_id=act.id,
                        scene_id=scene.id,
                        page=page_num,
                        line_type=ScriptLineType.DIALOGUE,
                    )
                    session.add(line)
                    session.flush()
                    lines.append(line.id)

            self.line_ids = lines

            # 6. Associate lines with revision
            for line_id in self.line_ids:
                assoc = ScriptLineRevisionAssociation(
                    revision_id=revision.id, line_id=line_id
                )
                session.add(assoc)

            # 7. Create diverse set of cues for comprehensive testing
            # Exact match cues (case variations)
            cue_exact1 = Cue(cue_type_id=cue_type_lighting.id, ident="LX 1")
            session.add(cue_exact1)
            session.flush()

            cue_exact2 = Cue(cue_type_id=cue_type_lighting.id, ident="lx 1")
            session.add(cue_exact2)
            session.flush()

            # Fuzzy match cues with varying similarity to "LX 1"
            cue_fuzzy1 = Cue(cue_type_id=cue_type_lighting.id, ident="LX 10")
            session.add(cue_fuzzy1)
            session.flush()

            cue_fuzzy2 = Cue(cue_type_id=cue_type_lighting.id, ident="LX 100")
            session.add(cue_fuzzy2)
            session.flush()

            cue_fuzzy3 = Cue(cue_type_id=cue_type_lighting.id, ident="LX 1.5")
            session.add(cue_fuzzy3)
            session.flush()

            cue_fuzzy4 = Cue(cue_type_id=cue_type_lighting.id, ident="LX 11")
            session.add(cue_fuzzy4)
            session.flush()

            cue_fuzzy5 = Cue(cue_type_id=cue_type_lighting.id, ident="LX 12")
            session.add(cue_fuzzy5)
            session.flush()

            cue_fuzzy6 = Cue(cue_type_id=cue_type_lighting.id, ident="LX 2")
            session.add(cue_fuzzy6)
            session.flush()

            cue_fuzzy7 = Cue(cue_type_id=cue_type_lighting.id, ident="LX 999")
            session.add(cue_fuzzy7)
            session.flush()

            # Additional cue for testing > 5 fuzzy matches
            cue_fuzzy8 = Cue(cue_type_id=cue_type_lighting.id, ident="LX 13")
            session.add(cue_fuzzy8)
            session.flush()

            # Cue with null ident for edge case testing
            cue_null = Cue(cue_type_id=cue_type_lighting.id, ident=None)
            session.add(cue_null)
            session.flush()

            # Different cue type (for filtering tests)
            cue_sound = Cue(cue_type_id=cue_type_sound.id, ident="SQ 1")
            session.add(cue_sound)
            session.flush()

            # Unique identifier for single exact match test
            cue_unique = Cue(cue_type_id=cue_type_lighting.id, ident="LX 42")
            session.add(cue_unique)
            session.flush()

            # 8. Create CueAssociations linking cues to lines
            cue_line_pairs = [
                (cue_exact1.id, self.line_ids[0]),
                (cue_exact2.id, self.line_ids[1]),
                (cue_fuzzy1.id, self.line_ids[2]),
                (cue_fuzzy2.id, self.line_ids[3]),
                (cue_fuzzy3.id, self.line_ids[4]),
                (cue_fuzzy4.id, self.line_ids[5]),
                (cue_fuzzy5.id, self.line_ids[6]),
                (cue_fuzzy6.id, self.line_ids[7]),
                (cue_fuzzy7.id, self.line_ids[8]),
                (cue_fuzzy8.id, self.line_ids[9]),
                (cue_null.id, self.line_ids[10]),
                (cue_sound.id, self.line_ids[11]),
                (cue_unique.id, self.line_ids[0]),
            ]

            for cue_id, line_id in cue_line_pairs:
                assoc = CueAssociation(
                    revision_id=revision.id, line_id=line_id, cue_id=cue_id
                )
                session.add(assoc)

            session.commit()

        # Set current show for @requires_show decorator
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    # A. Validation Tests (5 tests)

    def test_search_missing_identifier(self):
        """Test GET returns 400 when identifier parameter is missing."""
        response = self.fetch(
            f"/api/v1/show/cues/search?cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("Identifier parameter is required", response_body["message"])

    def test_search_empty_identifier(self):
        """Test GET returns 400 when identifier is empty string."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("Identifier parameter is required", response_body["message"])

    def test_search_missing_cue_type_id(self):
        """Test GET returns 400 when cue_type_id parameter is missing."""
        response = self.fetch("/api/v1/show/cues/search?identifier=LX%201")
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("Cue type ID parameter is required", response_body["message"])

    def test_search_invalid_cue_type_id(self):
        """Test GET returns 400 when cue_type_id is not an integer."""
        response = self.fetch(
            "/api/v1/show/cues/search?identifier=LX%201&cue_type_id=abc"
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual("Invalid cue_type_id parameter", response_body["message"])

    def test_search_no_current_revision(self):
        """Test GET returns 400 when script has no current revision."""
        # Create show without current revision
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Show 2", script_mode=ShowScriptType.FULL)
            session.add(show2)
            session.flush()
            show2_id = show2.id

            script2 = Script(show_id=show2.id)
            session.add(script2)
            session.flush()
            # Don't set current_revision
            script2.current_revision = None

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show2_id)

        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%201&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(400, response.code)
        response_body = tornado.escape.json_decode(response.body)
        self.assertEqual(
            "Script does not have a current revision", response_body["message"]
        )

        # Restore original show
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    # B. Exact Match Tests (4 tests) - PRIORITY: Case-insensitivity

    def test_search_exact_match_single_result(self):
        """Test exact match returns single result with proper structure."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%2042&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Validate structure
        self.assertIn("exact_matches", response_body)
        self.assertIn("suggestions", response_body)

        # Should have exactly 1 exact match
        self.assertEqual(1, len(response_body["exact_matches"]))
        self.assertEqual(0, len(response_body["suggestions"]))

        # Validate exact match structure
        match = response_body["exact_matches"][0]
        self.assertIn("cue", match)
        self.assertIn("cue_type", match)
        self.assertIn("location", match)

        # Validate cue fields
        self.assertEqual("LX 42", match["cue"]["ident"])

        # Validate location fields
        self.assertIn("page", match["location"])
        self.assertIn("line_id", match["location"])
        self.assertIn("act_id", match["location"])
        self.assertIn("scene_id", match["location"])

    def test_search_exact_match_multiple_results(self):
        """Test exact match returns multiple results for 'LX 1'."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%201&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Should have 2 exact matches ("LX 1" and "lx 1")
        self.assertEqual(2, len(response_body["exact_matches"]))
        self.assertEqual(0, len(response_body["suggestions"]))

        # Verify both matches are for "LX 1" (case-insensitive)
        idents = [match["cue"]["ident"] for match in response_body["exact_matches"]]
        self.assertIn("LX 1", idents)
        self.assertIn("lx 1", idents)

    def test_search_exact_match_case_insensitive(self):
        """Test searching 'lx 1' (lowercase) matches 'LX 1' (uppercase)."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=lx%201&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Should have 2 exact matches (case-insensitive)
        self.assertEqual(2, len(response_body["exact_matches"]))
        self.assertEqual(0, len(response_body["suggestions"]))

    def test_search_exact_match_case_variations(self):
        """Test searching 'Lx 1' (mixed case) matches both variations."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=Lx%201&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Should have 2 exact matches
        self.assertEqual(2, len(response_body["exact_matches"]))
        self.assertEqual(0, len(response_body["suggestions"]))

    # C. Fuzzy Match Tests (5 tests) - PRIORITY: Algorithm accuracy

    def test_search_fuzzy_match_no_exact_match(self):
        """Test fuzzy matching returns suggestions when no exact match."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%2015&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Should have no exact matches
        self.assertEqual(0, len(response_body["exact_matches"]))

        # Should have fuzzy suggestions
        self.assertGreater(len(response_body["suggestions"]), 0)

        # All suggestions should have similarity_score
        for suggestion in response_body["suggestions"]:
            self.assertIn("similarity_score", suggestion)
            self.assertGreater(suggestion["similarity_score"], 0.3)

    def test_search_fuzzy_match_top_5_limit(self):
        """Test fuzzy matching returns max 5 suggestions."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%201&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # This search has exact matches, so suggestions should be empty
        # Let's search for something with many fuzzy matches
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%2014&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Should have no exact matches
        self.assertEqual(0, len(response_body["exact_matches"]))

        # Should have at most 5 suggestions
        self.assertLessEqual(len(response_body["suggestions"]), 5)

    def test_search_fuzzy_match_score_ordering(self):
        """Test fuzzy suggestions are sorted by similarity_score descending."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%2015&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        suggestions = response_body["suggestions"]
        if len(suggestions) > 1:
            # Verify descending order
            for i in range(len(suggestions) - 1):
                self.assertGreaterEqual(
                    suggestions[i]["similarity_score"],
                    suggestions[i + 1]["similarity_score"],
                    "Suggestions should be sorted by similarity_score descending",
                )

    def test_search_fuzzy_match_similarity_threshold(self):
        """Test only matches with similarity score > 0.3 are included."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=ABC&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # All suggestions must have score > 0.3
        for suggestion in response_body["suggestions"]:
            self.assertGreater(
                suggestion["similarity_score"],
                0.3,
                "All suggestions should have similarity_score > 0.3",
            )

    def test_search_fuzzy_match_includes_scores(self):
        """Test each fuzzy suggestion contains valid similarity_score."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%2015&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        for suggestion in response_body["suggestions"]:
            self.assertIn("similarity_score", suggestion)
            score = suggestion["similarity_score"]
            self.assertIsInstance(score, float)
            self.assertGreater(score, 0.3)
            self.assertLessEqual(score, 1.0)

    # D. Cue Type Filtering Tests (3 tests) - PRIORITY: Type filtering

    def test_search_exact_match_respects_cue_type_filter(self):
        """Test exact match only returns cues of specified cue_type_id."""
        # Search for "SQ 1" with lighting cue type (should not match)
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=SQ%201&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Should have no exact matches (SQ 1 is a sound cue, not lighting)
        self.assertEqual(0, len(response_body["exact_matches"]))

        # Now search with correct cue type
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=SQ%201&cue_type_id={self.cue_type_sound_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Should have 1 exact match
        self.assertEqual(1, len(response_body["exact_matches"]))
        self.assertEqual("SQ 1", response_body["exact_matches"][0]["cue"]["ident"])

    def test_search_fuzzy_match_respects_cue_type_filter(self):
        """Test fuzzy match only returns cues of specified cue_type_id."""
        # Search with sound cue type (should only get sound cue suggestions)
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=SQ&cue_type_id={self.cue_type_sound_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # All results should be sound cues
        all_results = response_body["exact_matches"] + response_body["suggestions"]
        for result in all_results:
            self.assertEqual(
                self.cue_type_sound_id,
                result["cue_type"]["id"],
                "All results should match the specified cue_type_id",
            )

    def test_search_no_cues_of_specified_type(self):
        """Test empty results when cue type exists but has no cues."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=VD%201&cue_type_id={self.cue_type_empty_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Should have empty results
        self.assertEqual(0, len(response_body["exact_matches"]))
        self.assertEqual(0, len(response_body["suggestions"]))

    # E. Edge Cases & Integration (3 tests)

    def test_search_empty_database(self):
        """Test empty results when no cues exist at all."""
        # Create new show without any cues
        with self._app.get_db().sessionmaker() as session:
            show3 = Show(name="Empty Show", script_mode=ShowScriptType.FULL)
            session.add(show3)
            session.flush()
            show3_id = show3.id

            script3 = Script(show_id=show3.id)
            session.add(script3)
            session.flush()

            revision3 = ScriptRevision(
                script_id=script3.id, revision=1, description="Empty"
            )
            session.add(revision3)
            session.flush()

            script3.current_revision = revision3.id

            cue_type3 = CueType(
                show_id=show3.id,
                prefix="LX",
                description="Lighting",
                colour="#FF0000",
            )
            session.add(cue_type3)
            session.flush()
            cue_type3_id = cue_type3.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show3_id)

        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%201&cue_type_id={cue_type3_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Should have empty results
        self.assertEqual(0, len(response_body["exact_matches"]))
        self.assertEqual(0, len(response_body["suggestions"]))

        # Restore original show
        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def test_search_fuzzy_match_ignores_null_idents(self):
        """Test cues with null ident are excluded from fuzzy results."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=null&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        # Verify no results have null ident
        all_results = response_body["exact_matches"] + response_body["suggestions"]
        for result in all_results:
            self.assertIsNotNone(
                result["cue"]["ident"], "Null idents should be excluded"
            )

    def test_search_location_data_accuracy(self):
        """Test location fields are accurate for different pages."""
        response = self.fetch(
            f"/api/v1/show/cues/search?identifier=LX%2042&cue_type_id={self.cue_type_lighting_id}"
        )
        self.assertEqual(200, response.code)
        response_body = tornado.escape.json_decode(response.body)

        match = response_body["exact_matches"][0]
        location = match["location"]

        # Verify all location fields are present and valid
        self.assertIn("page", location)
        self.assertIn("line_id", location)
        self.assertIn("act_id", location)
        self.assertIn("scene_id", location)

        # Verify values are integers
        self.assertIsInstance(location["page"], int)
        self.assertIsInstance(location["line_id"], int)
        self.assertIsInstance(location["act_id"], int)
        self.assertIsInstance(location["scene_id"], int)

        # Verify page number is valid (1-3 in our test data)
        self.assertGreaterEqual(location["page"], 1)
        self.assertLessEqual(location["page"], 3)


class TestCueTypeImportController(DigiScriptTestCase):
    """Test suite for GET /api/v1/show/cues/types/import endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            # Current show — its cue types must be excluded from import results
            current_show = Show(name="Current Show", script_mode=ShowScriptType.FULL)
            session.add(current_show)
            session.flush()
            self.current_show_id = current_show.id

            current_cue_type = CueType(
                show_id=current_show.id,
                prefix="LX",
                description="Lighting",
                colour="#ff0000",
            )
            session.add(current_cue_type)
            session.flush()
            self.current_cue_type_id = current_cue_type.id

            # Other show — its cue types should appear in import results
            other_show = Show(name="Other Show", script_mode=ShowScriptType.FULL)
            session.add(other_show)
            session.flush()
            self.other_show_id = other_show.id

            other_cue_type = CueType(
                show_id=other_show.id,
                prefix="SND",
                description="Sound",
                colour="#00ff00",
            )
            session.add(other_cue_type)
            session.flush()
            self.other_cue_type_id = other_cue_type.id

            # Empty show — no cue types, must not appear in import results
            empty_show = Show(name="Empty Show", script_mode=ShowScriptType.FULL)
            session.add(empty_show)
            session.flush()
            self.empty_show_id = empty_show.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.current_show_id)

    def test_get_import_requires_show(self):
        """Test that the endpoint returns 400 when no current show is set."""
        self._app.digi_settings.settings["current_show"].set_value(None)
        response = self.fetch("/api/v1/show/cues/types/import")
        self.assertEqual(400, response.code)

    def test_get_import_excludes_current_show(self):
        """Test that the current show's cue types are not included in the response."""
        response = self.fetch("/api/v1/show/cues/types/import")
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        group_ids = [g["id"] for g in body["cue_type_groups"]]
        self.assertNotIn(self.current_show_id, group_ids)

    def test_get_import_includes_other_shows(self):
        """Test that other shows with cue types are included with correct data."""
        response = self.fetch("/api/v1/show/cues/types/import")
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)

        other_group = next(
            (g for g in body["cue_type_groups"] if g["id"] == self.other_show_id), None
        )
        self.assertIsNotNone(other_group)
        self.assertEqual("Other Show", other_group["name"])
        self.assertEqual(1, len(other_group["cue_types"]))

        cue_type = other_group["cue_types"][0]
        self.assertEqual("SND", cue_type["prefix"])
        self.assertEqual("Sound", cue_type["description"])
        self.assertEqual("#00ff00", cue_type["colour"])

    def test_get_import_skips_shows_with_no_cue_types(self):
        """Test that shows with no cue types are not included in the response."""
        response = self.fetch("/api/v1/show/cues/types/import")
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        group_ids = [g["id"] for g in body["cue_type_groups"]]
        self.assertNotIn(self.empty_show_id, group_ids)

    def test_get_import_returns_correct_structure(self):
        """Test that the response contains the expected top-level structure."""
        response = self.fetch("/api/v1/show/cues/types/import")
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)

        self.assertIn("cue_type_groups", body)
        self.assertIsInstance(body["cue_type_groups"], list)

        for group in body["cue_type_groups"]:
            self.assertIn("id", group)
            self.assertIn("name", group)
            self.assertIn("cue_types", group)
            self.assertIsInstance(group["cue_types"], list)


class TestCueTypesController(DigiScriptTestCase):
    """Test suite for POST /api/v1/show/cues/types endpoint."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.admin_token = self._create_and_login_admin()
        self.user_token = self._create_and_login_user(self.admin_token)

        with self._app.get_db().sessionmaker() as session:
            admin = session.scalars(
                select(User).where(User.username == "admin")
            ).first()
            self.admin_id = admin.id
            user = session.scalars(select(User).where(User.username == "user")).first()
            self.user_id = user.id
            show = session.get(Show, self.show_id)
            self._app.rbac.give_role(user, show, Role.WRITE)

    def test_post_cue_type_grants_all_roles_to_creator(self):
        """Creating a cue type grants READ|WRITE|EXECUTE to the creating user."""
        response = self.fetch(
            "/api/v1/show/cues/types",
            method="POST",
            body=tornado.escape.json_encode(
                {"prefix": "LX", "description": "Lighting", "colour": "#ff0000"}
            ),
            headers={"Authorization": f"Bearer {self.user_token}"},
        )
        self.assertEqual(200, response.code)
        cue_type_id = tornado.escape.json_decode(response.body)["id"]

        with self._app.get_db().sessionmaker() as session:
            user = session.get(User, self.user_id)
            cue_type = session.get(CueType, cue_type_id)
            self.assertTrue(
                self._app.rbac.has_role(
                    user, cue_type, Role.READ | Role.WRITE | Role.EXECUTE
                )
            )

    def test_post_cue_type_admin_also_gets_grant(self):
        """Creating a cue type as an admin still writes the RBAC grant."""
        response = self.fetch(
            "/api/v1/show/cues/types",
            method="POST",
            body=tornado.escape.json_encode(
                {"prefix": "SQ", "description": "Sound", "colour": "#00ff00"}
            ),
            headers={"Authorization": f"Bearer {self.admin_token}"},
        )
        self.assertEqual(200, response.code)
        cue_type_id = tornado.escape.json_decode(response.body)["id"]

        with self._app.get_db().sessionmaker() as session:
            admin = session.get(User, self.admin_id)
            cue_type = session.get(CueType, cue_type_id)
            self.assertTrue(
                self._app.rbac.has_role(
                    admin, cue_type, Role.READ | Role.WRITE | Role.EXECUTE
                )
            )


class TestCueGroups(DigiScriptTestCase):
    """Tests for POST/PATCH/DELETE /api/v1/show/cues/groups."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
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

            act = Act(show_id=show.id, name="Act 1")
            session.add(act)
            session.flush()

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()

            line = ScriptLine(
                act_id=act.id,
                scene_id=scene.id,
                page=1,
                line_type=ScriptLineType.DIALOGUE,
            )
            session.add(line)
            session.flush()
            self.line_id = line.id

            spacing_line = ScriptLine(
                act_id=act.id,
                scene_id=scene.id,
                page=1,
                line_type=ScriptLineType.SPACING,
            )
            session.add(spacing_line)
            session.flush()
            self.spacing_line_id = spacing_line.id

            assoc = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=line.id
            )
            session.add(assoc)
            assoc2 = ScriptLineRevisionAssociation(
                revision_id=revision.id, line_id=spacing_line.id
            )
            session.add(assoc2)

            cue_type = CueType(
                show_id=show.id, prefix="LX", description="Lighting", colour="#ff0000"
            )
            session.add(cue_type)
            session.flush()
            self.cue_type_id = cue_type.id

            test_credential = "test"
            admin = User(username="admin", is_admin=True, password=test_credential)
            session.add(admin)
            session.flush()
            self.user_id = admin.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)
        self.token = self._app.jwt_service.create_access_token(
            data={"user_id": self.user_id}
        )

    def _create_group(self, cues=None, label_override=None):
        """Helper: POST a cue group and return the response."""
        if cues is None:
            cues = [{"ident": str(i), "sortOrder": i - 1} for i in range(1, 4)]
        body = {
            "cueTypeId": self.cue_type_id,
            "lineId": self.line_id,
            "cues": cues,
        }
        if label_override is not None:
            body["labelOverride"] = label_override
        return self.fetch(
            "/api/v1/show/cues/groups",
            method="POST",
            body=tornado.escape.json_encode(body),
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def test_post_creates_group_and_cues(self):
        """POST /cues/groups creates CueGroup, Cue rows, and CueAssociation rows."""
        response = self._create_group()
        self.assertEqual(200, response.code)
        body = tornado.escape.json_decode(response.body)
        self.assertIn("id", body)
        group_id = body["id"]

        with self._app.get_db().sessionmaker() as session:
            group = session.get(CueGroup, group_id)
            self.assertIsNotNone(group)
            self.assertEqual(self.cue_type_id, group.cue_type_id)
            self.assertIsNone(group.label_override)

            assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.group_id == group_id,
                    CueAssociation.revision_id == self.revision_id,
                )
            ).all()
            self.assertEqual(3, len(assocs))
            sort_orders = sorted(a.sort_order for a in assocs)
            self.assertEqual([0, 1, 2], sort_orders)

    def test_post_with_label_override(self):
        """POST stores label_override on the CueGroup."""
        response = self._create_group(label_override="Music Intro")
        self.assertEqual(200, response.code)
        group_id = tornado.escape.json_decode(response.body)["id"]

        with self._app.get_db().sessionmaker() as session:
            group = session.get(CueGroup, group_id)
            self.assertEqual("Music Intro", group.label_override)

    def test_get_cues_includes_group_id_and_sort_order(self):
        """GET /cues response includes group_id, sort_order, and cue_groups."""
        response = self._create_group()
        group_id = tornado.escape.json_decode(response.body)["id"]

        get_response = self.fetch("/api/v1/show/cues")
        self.assertEqual(200, get_response.code)
        data = tornado.escape.json_decode(get_response.body)

        self.assertIn("cue_groups", data)
        group_ids_returned = [g["id"] for g in data["cue_groups"]]
        self.assertIn(group_id, group_ids_returned)

        line_cues = data["cues"].get(str(self.line_id), [])
        for cue in line_cues:
            self.assertIn("group_id", cue)
            self.assertIn("sort_order", cue)
            self.assertEqual(group_id, cue["group_id"])

    def test_post_rejects_spacing_line(self):
        """POST /cues/groups rejects SPACING lines."""
        body = {
            "cueTypeId": self.cue_type_id,
            "lineId": self.spacing_line_id,
            "cues": [{"ident": "1", "sortOrder": 0}],
        }
        response = self.fetch(
            "/api/v1/show/cues/groups",
            method="POST",
            body=tornado.escape.json_encode(body),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    def test_post_rejects_empty_cue_list(self):
        """POST with no cues returns 400."""
        body = {
            "cueTypeId": self.cue_type_id,
            "lineId": self.line_id,
            "cues": [],
        }
        response = self.fetch(
            "/api/v1/show/cues/groups",
            method="POST",
            body=tornado.escape.json_encode(body),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(400, response.code)

    def test_patch_updates_label_override(self):
        """PATCH /cues/groups updates label_override."""
        create_resp = self._create_group()
        group_id = tornado.escape.json_decode(create_resp.body)["id"]

        with self._app.get_db().sessionmaker() as session:
            assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.group_id == group_id,
                    CueAssociation.revision_id == self.revision_id,
                )
            ).all()
            existing_cues = [
                {"id": a.cue_id, "ident": a.cue.ident, "sortOrder": a.sort_order}
                for a in assocs
            ]

        patch_body = {
            "groupId": group_id,
            "lineId": self.line_id,
            "labelOverride": "New Label",
            "cues": existing_cues,
        }
        response = self.fetch(
            "/api/v1/show/cues/groups",
            method="PATCH",
            body=tornado.escape.json_encode(patch_body),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            group = session.get(CueGroup, group_id)
            self.assertEqual("New Label", group.label_override)

    def test_patch_adds_and_removes_cues(self):
        """PATCH reconciles cue membership — adds new, removes absent."""
        create_resp = self._create_group(
            cues=[
                {"ident": "1", "sortOrder": 0},
                {"ident": "2", "sortOrder": 1},
            ]
        )
        group_id = tornado.escape.json_decode(create_resp.body)["id"]

        with self._app.get_db().sessionmaker() as session:
            assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.group_id == group_id,
                    CueAssociation.revision_id == self.revision_id,
                )
            ).all()
            # Keep cue "1", drop cue "2", add cue "3"
            keep_assoc = next(a for a in assocs if a.cue.ident == "1")

        patch_body = {
            "groupId": group_id,
            "lineId": self.line_id,
            "cues": [
                {"id": keep_assoc.cue_id, "ident": "1", "sortOrder": 0},
                {"ident": "3", "sortOrder": 1},
            ],
        }
        response = self.fetch(
            "/api/v1/show/cues/groups",
            method="PATCH",
            body=tornado.escape.json_encode(patch_body),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.group_id == group_id,
                    CueAssociation.revision_id == self.revision_id,
                )
            ).all()
            self.assertEqual(2, len(assocs))
            idents = {a.cue.ident for a in assocs}
            self.assertEqual({"1", "3"}, idents)

    def test_delete_removes_group_and_cleans_up(self):
        """DELETE /cues/groups removes associations and orphaned CueGroup/Cue rows."""
        create_resp = self._create_group()
        group_id = tornado.escape.json_decode(create_resp.body)["id"]

        with self._app.get_db().sessionmaker() as session:
            assocs = session.scalars(
                select(CueAssociation).where(CueAssociation.group_id == group_id)
            ).all()
            cue_ids = [a.cue_id for a in assocs]

        response = self.fetch(
            f"/api/v1/show/cues/groups?groupId={group_id}&lineId={self.line_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            group = session.get(CueGroup, group_id)
            self.assertIsNone(group)
            for cue_id in cue_ids:
                cue = session.get(Cue, cue_id)
                self.assertIsNone(cue)

    def test_revision_copy_forward_preserves_group(self):
        """Creating a new revision copies group_id and sort_order."""
        create_resp = self._create_group(
            cues=[
                {"ident": "1", "sortOrder": 0},
                {"ident": "2", "sortOrder": 1},
            ]
        )
        group_id = tornado.escape.json_decode(create_resp.body)["id"]

        response = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode(
                {"description": "Rev 2", "sourceRevision": self.revision_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)
        new_rev_id = tornado.escape.json_decode(response.body)["id"]

        with self._app.get_db().sessionmaker() as session:
            new_assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.revision_id == new_rev_id,
                    CueAssociation.group_id == group_id,
                )
            ).all()
            self.assertEqual(2, len(new_assocs))
            sort_orders = sorted(a.sort_order for a in new_assocs)
            self.assertEqual([0, 1], sort_orders)

    def test_mixed_individual_and_group_on_same_line(self):
        """A line can have both individual cues and cue group members."""
        self._create_group(cues=[{"ident": "1", "sortOrder": 0}])

        individual_body = {
            "cueType": self.cue_type_id,
            "ident": "solo",
            "lineId": self.line_id,
        }
        response = self.fetch(
            "/api/v1/show/cues",
            method="POST",
            body=tornado.escape.json_encode(individual_body),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        get_resp = self.fetch("/api/v1/show/cues")
        data = tornado.escape.json_decode(get_resp.body)
        line_cues = data["cues"].get(str(self.line_id), [])
        self.assertEqual(2, len(line_cues))
        group_cues = [c for c in line_cues if c["group_id"] is not None]
        solo_cues = [c for c in line_cues if c["group_id"] is None]
        self.assertEqual(1, len(group_cues))
        self.assertEqual(1, len(solo_cues))
        self.assertEqual("solo", solo_cues[0]["ident"])

    def test_patch_forks_group_when_shared_across_revisions(self):
        """PATCH creates a new CueGroup for the current revision when another revision
        references the same group, leaving the other revision's associations untouched."""
        # Create group in revision 1
        create_resp = self._create_group(
            cues=[
                {"ident": "1", "sortOrder": 0},
                {"ident": "2", "sortOrder": 1},
            ]
        )
        original_group_id = tornado.escape.json_decode(create_resp.body)["id"]

        # Create revision 2 as a copy of revision 1
        rev_resp = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode(
                {"description": "Rev 2", "sourceRevision": self.revision_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, rev_resp.code)
        rev2_id = tornado.escape.json_decode(rev_resp.body)["id"]

        # Switch current revision to revision 2
        with self._app.get_db().sessionmaker() as session:
            script = session.scalars(
                select(Script).where(Script.show_id == self.show_id)
            ).first()
            script.current_revision = rev2_id
            session.commit()

        # PATCH the group while in revision 2 (same cues, just triggers fork check)
        with self._app.get_db().sessionmaker() as session:
            assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.group_id == original_group_id,
                    CueAssociation.revision_id == rev2_id,
                )
            ).all()
            existing_cues = [
                {"id": a.cue_id, "ident": a.cue.ident, "sortOrder": a.sort_order}
                for a in assocs
            ]

        patch_body = {
            "groupId": original_group_id,
            "lineId": self.line_id,
            "labelOverride": "Forked Label",
            "cues": existing_cues,
        }
        patch_resp = self.fetch(
            "/api/v1/show/cues/groups",
            method="PATCH",
            body=tornado.escape.json_encode(patch_body),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, patch_resp.code)

        with self._app.get_db().sessionmaker() as session:
            # Revision 2's associations should now reference a NEW group
            rev2_assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.revision_id == rev2_id,
                    CueAssociation.line_id == self.line_id,
                )
            ).all()
            rev2_group_ids = {a.group_id for a in rev2_assocs}
            self.assertEqual(
                1, len(rev2_group_ids), "Rev 2 should have exactly one group"
            )
            forked_group_id = next(iter(rev2_group_ids))
            self.assertNotEqual(
                original_group_id,
                forked_group_id,
                "Rev 2 should reference a new (forked) CueGroup",
            )

            # Verify the forked group has the updated label
            forked_group = session.get(CueGroup, forked_group_id)
            self.assertEqual("Forked Label", forked_group.label_override)

            # Revision 1's associations must still reference the original group
            rev1_assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.revision_id == self.revision_id,
                    CueAssociation.group_id == original_group_id,
                )
            ).all()
            self.assertEqual(
                2, len(rev1_assocs), "Rev 1 associations should be unchanged"
            )

    def test_delete_preserves_group_when_other_revision_references_it(self):
        """DELETE removes associations only for the current revision; the CueGroup
        row is retained as long as another revision still references it."""
        # Create group in revision 1
        create_resp = self._create_group()
        group_id = tornado.escape.json_decode(create_resp.body)["id"]

        # Create revision 2 (copy forward — group_id carries over)
        rev_resp = self.fetch(
            "/api/v1/show/script/revisions",
            method="POST",
            body=tornado.escape.json_encode(
                {"description": "Rev 2", "sourceRevision": self.revision_id}
            ),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, rev_resp.code)
        rev2_id = tornado.escape.json_decode(rev_resp.body)["id"]

        # Switch current revision to revision 2
        with self._app.get_db().sessionmaker() as session:
            script = session.scalars(
                select(Script).where(Script.show_id == self.show_id)
            ).first()
            script.current_revision = rev2_id
            session.commit()

        # DELETE the group from revision 2
        delete_resp = self.fetch(
            f"/api/v1/show/cues/groups?groupId={group_id}&lineId={self.line_id}",
            method="DELETE",
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, delete_resp.code)

        with self._app.get_db().sessionmaker() as session:
            # CueGroup must still exist — revision 1 still references it
            group = session.get(CueGroup, group_id)
            self.assertIsNotNone(
                group, "CueGroup must survive when another revision references it"
            )

            # Revision 2 must have no associations for this group
            rev2_assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.revision_id == rev2_id,
                    CueAssociation.group_id == group_id,
                )
            ).all()
            self.assertEqual(
                0,
                len(rev2_assocs),
                "Rev 2 should have no group associations after delete",
            )

            # Revision 1's associations must be intact
            rev1_assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.revision_id == self.revision_id,
                    CueAssociation.group_id == group_id,
                )
            ).all()
            self.assertGreater(
                len(rev1_assocs), 0, "Rev 1 associations must remain untouched"
            )

    def test_patch_removes_orphaned_cue(self):
        """When PATCH removes a cue from a group, the orphaned Cue row is deleted."""
        create_resp = self._create_group(
            cues=[
                {"ident": "1", "sortOrder": 0},
                {"ident": "2", "sortOrder": 1},
            ]
        )
        group_id = tornado.escape.json_decode(create_resp.body)["id"]

        with self._app.get_db().sessionmaker() as session:
            assocs = session.scalars(
                select(CueAssociation).where(
                    CueAssociation.group_id == group_id,
                    CueAssociation.revision_id == self.revision_id,
                )
            ).all()
            keep_assoc = next(a for a in assocs if a.cue.ident == "1")
            drop_cue_id = next(a.cue_id for a in assocs if a.cue.ident == "2")

        # PATCH keeping only cue "1"
        patch_body = {
            "groupId": group_id,
            "lineId": self.line_id,
            "cues": [{"id": keep_assoc.cue_id, "ident": "1", "sortOrder": 0}],
        }
        response = self.fetch(
            "/api/v1/show/cues/groups",
            method="PATCH",
            body=tornado.escape.json_encode(patch_body),
            headers={"Authorization": f"Bearer {self.token}"},
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            dropped_cue = session.get(Cue, drop_cue_id)
            self.assertIsNone(
                dropped_cue, "Orphaned Cue must be deleted after removal from group"
            )

    def test_patch_and_delete_require_no_live_session(self):
        """PATCH and DELETE on /cues/groups are blocked when a live session exists."""
        create_resp = self._create_group()
        group_id = tornado.escape.json_decode(create_resp.body)["id"]

        with self._app.get_db().sessionmaker() as session:
            show_session = ShowSession(
                show_id=self.show_id,
                script_revision_id=self.revision_id,
            )
            session.add(show_session)
            session.flush()
            session_id = show_session.id
            show = session.get(Show, self.show_id)
            show.current_session_id = session_id
            session.commit()

        try:
            patch_body = {
                "groupId": group_id,
                "lineId": self.line_id,
                "cues": [{"ident": "1", "sortOrder": 0}],
            }
            patch_resp = self.fetch(
                "/api/v1/show/cues/groups",
                method="PATCH",
                body=tornado.escape.json_encode(patch_body),
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.assertEqual(409, patch_resp.code)

            delete_resp = self.fetch(
                f"/api/v1/show/cues/groups?groupId={group_id}&lineId={self.line_id}",
                method="DELETE",
                headers={"Authorization": f"Bearer {self.token}"},
            )
            self.assertEqual(409, delete_resp.code)
        finally:
            with self._app.get_db().sessionmaker() as session:
                show = session.get(Show, self.show_id)
                show.current_session_id = None
                ss = session.get(ShowSession, session_id)
                if ss:
                    session.delete(ss)
                session.commit()
