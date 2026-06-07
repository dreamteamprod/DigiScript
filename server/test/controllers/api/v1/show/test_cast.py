import tornado.escape

from models.script import (
    Script,
    ScriptCuts,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptLineType,
    ScriptRevision,
)
from models.show import (
    Act,
    Cast,
    Character,
    CharacterGroup,
    Scene,
    Show,
    ShowScriptType,
)
from test.conftest import DigiScriptTestCase


class TestCastStatsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/cast/stats endpoint."""

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
            self.script_id = script.id

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
            self.act_id = act.id

            scene = Scene(show_id=show.id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            self.scene_id = scene.id

            cast_member = Cast(show_id=show.id, first_name="Jane", last_name="Doe")
            session.add(cast_member)
            session.flush()
            self.cast_id = cast_member.id

            character = Character(
                show_id=show.id, name="Protagonist", played_by=cast_member.id
            )
            session.add(character)
            session.flush()
            self.character_id = character.id

            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def _make_dialogue_line(
        self, session, act_id, scene_id, character_id=None, character_group_id=None
    ):
        """Helper: create a DIALOGUE line + part + revision association."""
        line = ScriptLine(
            act_id=act_id, scene_id=scene_id, page=1, line_type=ScriptLineType.DIALOGUE
        )
        session.add(line)
        session.flush()
        part = ScriptLinePart(
            line_id=line.id,
            part_index=0,
            character_id=character_id,
            character_group_id=character_group_id,
            line_text="Test line",
        )
        session.add(part)
        session.flush()
        assoc = ScriptLineRevisionAssociation(
            revision_id=self.revision_id, line_id=line.id
        )
        session.add(assoc)
        session.commit()
        return line.id, part.id

    def test_get_cast_stats(self):
        """Endpoint returns 200 with line_counts key."""
        response = self.fetch("/api/v1/show/cast/stats")
        self.assertEqual(200, response.code)
        self.assertIn("line_counts", tornado.escape.json_decode(response.body))

    def test_get_cast_stats_no_script(self):
        """Returns error when no script exists for the show."""
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Show 2", script_mode=ShowScriptType.FULL)
            session.add(show2)
            session.flush()
            show2_id = show2.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show2_id)

        response = self.fetch("/api/v1/show/cast/stats")
        self.assertNotEqual(200, response.code)

    def test_stats_dialogue_line_counted(self):
        """A dialogue line assigned to a character with a cast member is counted."""
        with self._app.get_db().sessionmaker() as session:
            self._make_dialogue_line(
                session, self.act_id, self.scene_id, character_id=self.character_id
            )

        body = tornado.escape.json_decode(self.fetch("/api/v1/show/cast/stats").body)
        line_counts = body["line_counts"]

        # Keys are serialised as strings in JSON
        self.assertIn(str(self.cast_id), line_counts)
        self.assertIn(str(self.act_id), line_counts[str(self.cast_id)])
        self.assertEqual(
            1,
            line_counts[str(self.cast_id)][str(self.act_id)][str(self.scene_id)],
        )

    def test_stats_character_without_cast_excluded(self):
        """A dialogue line for a character with no cast member is not counted."""
        with self._app.get_db().sessionmaker() as session:
            uncast = Character(show_id=self.show_id, name="Uncast", played_by=None)
            session.add(uncast)
            session.flush()
            uncast_id = uncast.id
            session.commit()

        with self._app.get_db().sessionmaker() as session:
            self._make_dialogue_line(
                session, self.act_id, self.scene_id, character_id=uncast_id
            )

        body = tornado.escape.json_decode(self.fetch("/api/v1/show/cast/stats").body)
        self.assertEqual({}, body["line_counts"])

    def test_stats_cut_line_excluded(self):
        """A line part with a ScriptCuts entry for the current revision is excluded."""
        with self._app.get_db().sessionmaker() as session:
            _, part_id = self._make_dialogue_line(
                session, self.act_id, self.scene_id, character_id=self.character_id
            )

        with self._app.get_db().sessionmaker() as session:
            session.add(ScriptCuts(line_part_id=part_id, revision_id=self.revision_id))
            session.commit()

        body = tornado.escape.json_decode(self.fetch("/api/v1/show/cast/stats").body)
        self.assertEqual({}, body["line_counts"])

    def test_stats_stage_direction_excluded(self):
        """Non-dialogue lines (stage directions) are not counted."""
        with self._app.get_db().sessionmaker() as session:
            line = ScriptLine(
                act_id=self.act_id,
                scene_id=self.scene_id,
                page=1,
                line_type=ScriptLineType.STAGE_DIRECTION,
            )
            session.add(line)
            session.flush()
            assoc = ScriptLineRevisionAssociation(
                revision_id=self.revision_id, line_id=line.id
            )
            session.add(assoc)
            session.commit()

        body = tornado.escape.json_decode(self.fetch("/api/v1/show/cast/stats").body)
        self.assertEqual({}, body["line_counts"])

    def test_stats_character_group_expands_to_members(self):
        """A character group line counts each cast-assigned group member separately."""
        with self._app.get_db().sessionmaker() as session:
            cast2 = Cast(show_id=self.show_id, first_name="John", last_name="Smith")
            session.add(cast2)
            session.flush()
            cast2_id = cast2.id

            char2 = Character(show_id=self.show_id, name="Sidekick", played_by=cast2_id)
            session.add(char2)
            session.flush()

            char1 = session.get(Character, self.character_id)
            group = CharacterGroup(show_id=self.show_id, name="Ensemble")
            group.characters = [char1, char2]
            session.add(group)
            session.flush()
            group_id = group.id
            session.commit()

        with self._app.get_db().sessionmaker() as session:
            self._make_dialogue_line(
                session, self.act_id, self.scene_id, character_group_id=group_id
            )

        body = tornado.escape.json_decode(self.fetch("/api/v1/show/cast/stats").body)
        line_counts = body["line_counts"]

        self.assertEqual(
            1,
            line_counts[str(self.cast_id)][str(self.act_id)][str(self.scene_id)],
        )
        self.assertEqual(
            1,
            line_counts[str(cast2_id)][str(self.act_id)][str(self.scene_id)],
        )

    def test_stats_multiple_acts_and_scenes(self):
        """Counts are correctly attributed per act and scene."""
        with self._app.get_db().sessionmaker() as session:
            act2 = Act(show_id=self.show_id, name="Act 2")
            session.add(act2)
            session.flush()
            act2_id = act2.id

            scene2 = Scene(show_id=self.show_id, act_id=act2.id, name="Scene 2")
            session.add(scene2)
            session.flush()
            scene2_id = scene2.id
            session.commit()

        with self._app.get_db().sessionmaker() as session:
            # One line in act1/scene1, two lines in act2/scene2
            self._make_dialogue_line(
                session, self.act_id, self.scene_id, character_id=self.character_id
            )
        with self._app.get_db().sessionmaker() as session:
            self._make_dialogue_line(
                session, act2_id, scene2_id, character_id=self.character_id
            )
        with self._app.get_db().sessionmaker() as session:
            self._make_dialogue_line(
                session, act2_id, scene2_id, character_id=self.character_id
            )

        body = tornado.escape.json_decode(self.fetch("/api/v1/show/cast/stats").body)
        counts = body["line_counts"][str(self.cast_id)]

        self.assertEqual(1, counts[str(self.act_id)][str(self.scene_id)])
        self.assertEqual(2, counts[str(act2_id)][str(scene2_id)])
