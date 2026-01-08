import tornado.escape
from sqlalchemy import select

from models.cue import Cue, CueAssociation, CueType
from models.script import (
    Script,
    ScriptLine,
    ScriptLineRevisionAssociation,
    ScriptLineType,
    ScriptRevision,
)
from models.show import Act, Scene, Show, ShowScriptType
from models.user import User
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
            admin = User(username="admin", is_admin=True, password="test")
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
