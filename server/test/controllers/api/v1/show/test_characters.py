import tornado.escape
from sqlalchemy import select

from models.mics import Microphone, MicrophoneAllocation
from models.script import (
    Script,
    ScriptCuts,
    ScriptLine,
    ScriptLinePart,
    ScriptLineRevisionAssociation,
    ScriptLineType,
    ScriptRevision,
)
from models.show import Act, Character, CharacterGroup, Scene, Show, ShowScriptType
from test.conftest import DigiScriptTestCase


class TestCharacterStatsController(DigiScriptTestCase):
    """Test suite for /api/v1/show/character/stats endpoint."""

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

            character = Character(show_id=show.id, name="Protagonist")
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

    def test_get_character_stats(self):
        """Endpoint returns 200 with line_counts key."""
        response = self.fetch("/api/v1/show/character/stats")
        self.assertEqual(200, response.code)
        self.assertIn("line_counts", tornado.escape.json_decode(response.body))

    def test_get_character_stats_no_script(self):
        """Returns error when no script exists for the show."""
        with self._app.get_db().sessionmaker() as session:
            show2 = Show(name="Show 2", script_mode=ShowScriptType.FULL)
            session.add(show2)
            session.flush()
            show2_id = show2.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(show2_id)

        response = self.fetch("/api/v1/show/character/stats")
        self.assertNotEqual(200, response.code)

    def test_stats_dialogue_line_counted(self):
        """A dialogue line assigned to a character is counted under that character."""
        with self._app.get_db().sessionmaker() as session:
            self._make_dialogue_line(
                session, self.act_id, self.scene_id, character_id=self.character_id
            )

        body = tornado.escape.json_decode(
            self.fetch("/api/v1/show/character/stats").body
        )
        line_counts = body["line_counts"]

        self.assertIn(str(self.character_id), line_counts)
        self.assertEqual(
            1,
            line_counts[str(self.character_id)][str(self.act_id)][str(self.scene_id)],
        )

    def test_stats_cut_line_excluded(self):
        """A line part with a ScriptCuts entry for the current revision is excluded."""
        with self._app.get_db().sessionmaker() as session:
            _, part_id = self._make_dialogue_line(
                session, self.act_id, self.scene_id, character_id=self.character_id
            )

        with self._app.get_db().sessionmaker() as session:
            session.add(ScriptCuts(line_part_id=part_id, revision_id=self.revision_id))
            session.commit()

        body = tornado.escape.json_decode(
            self.fetch("/api/v1/show/character/stats").body
        )
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

        body = tornado.escape.json_decode(
            self.fetch("/api/v1/show/character/stats").body
        )
        self.assertEqual({}, body["line_counts"])

    def test_stats_character_group_expands_to_members(self):
        """A character group line counts each member character separately."""
        with self._app.get_db().sessionmaker() as session:
            char2 = Character(show_id=self.show_id, name="Sidekick")
            session.add(char2)
            session.flush()
            char2_id = char2.id

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

        body = tornado.escape.json_decode(
            self.fetch("/api/v1/show/character/stats").body
        )
        line_counts = body["line_counts"]

        self.assertEqual(
            1,
            line_counts[str(self.character_id)][str(self.act_id)][str(self.scene_id)],
        )
        self.assertEqual(
            1,
            line_counts[str(char2_id)][str(self.act_id)][str(self.scene_id)],
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

        body = tornado.escape.json_decode(
            self.fetch("/api/v1/show/character/stats").body
        )
        counts = body["line_counts"][str(self.character_id)]

        self.assertEqual(1, counts[str(self.act_id)][str(self.scene_id)])
        self.assertEqual(2, counts[str(act2_id)][str(scene2_id)])


class TestCharacterMergeController(DigiScriptTestCase):
    """Test suite for POST /api/v1/show/character/merge endpoint."""

    def setUp(self):
        super().setUp()
        self.token = self._create_and_login_admin()

        with self._app.get_db().sessionmaker() as session:
            show = Show(name="Test Show", script_mode=ShowScriptType.FULL)
            session.add(show)
            session.flush()
            self.show_id = show.id

            source = Character(show_id=show.id, name="Source")
            destination = Character(show_id=show.id, name="Destination")
            session.add(source)
            session.add(destination)
            session.flush()
            self.source_id = source.id
            self.destination_id = destination.id
            session.commit()

        self._app.digi_settings.settings["current_show"].set_value(self.show_id)

    def _merge(self, body: dict) -> object:
        return self.fetch(
            "/api/v1/show/character/merge",
            method="POST",
            body=tornado.escape.json_encode(body),
            headers={"Authorization": f"Bearer {self.token}"},
        )

    def test_merge_missing_source_id(self):
        """POST with no source_id returns 400."""
        response = self._merge({"destination_id": self.destination_id})
        self.assertEqual(400, response.code)

    def test_merge_missing_destination_id(self):
        """POST with no destination_id returns 400."""
        response = self._merge({"source_id": self.source_id})
        self.assertEqual(400, response.code)

    def test_merge_same_character(self):
        """POST with identical source and destination returns 400."""
        response = self._merge(
            {"source_id": self.source_id, "destination_id": self.source_id}
        )
        self.assertEqual(400, response.code)

    def test_merge_source_not_found(self):
        """POST with a nonexistent source_id returns 404."""
        response = self._merge(
            {"source_id": 99999, "destination_id": self.destination_id}
        )
        self.assertEqual(404, response.code)

    def test_merge_destination_not_found(self):
        """POST with a nonexistent destination_id returns 404."""
        response = self._merge({"source_id": self.source_id, "destination_id": 99999})
        self.assertEqual(404, response.code)

    def test_merge_cross_show_source(self):
        """POST with a source character from a different show returns 404."""
        with self._app.get_db().sessionmaker() as session:
            other_show = Show(name="Other Show", script_mode=ShowScriptType.FULL)
            session.add(other_show)
            session.flush()
            foreign_char = Character(show_id=other_show.id, name="Foreign")
            session.add(foreign_char)
            session.flush()
            foreign_id = foreign_char.id
            session.commit()

        response = self._merge(
            {"source_id": foreign_id, "destination_id": self.destination_id}
        )
        self.assertEqual(404, response.code)

    def test_merge_deletes_source(self):
        """Successful merge removes the source character."""
        response = self._merge(
            {"source_id": self.source_id, "destination_id": self.destination_id}
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            remaining = session.scalars(
                select(Character).where(Character.show_id == self.show_id)
            ).all()
            names = [c.name for c in remaining]
        self.assertNotIn("Source", names)
        self.assertIn("Destination", names)

    def test_merge_transfers_script_line_parts(self):
        """Merge updates all ScriptLinePart rows for the source to the destination."""
        with self._app.get_db().sessionmaker() as session:
            act = Act(show_id=self.show_id, name="Act 1")
            session.add(act)
            session.flush()
            scene = Scene(show_id=self.show_id, act_id=act.id, name="Scene 1")
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
            part = ScriptLinePart(
                line_id=line.id,
                part_index=0,
                character_id=self.source_id,
            )
            session.add(part)
            session.flush()
            part_id = part.id
            session.commit()

        response = self._merge(
            {"source_id": self.source_id, "destination_id": self.destination_id}
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            updated_part = session.get(ScriptLinePart, part_id)
            self.assertEqual(self.destination_id, updated_part.character_id)

    def test_merge_updates_character_groups(self):
        """Merge adds destination to groups that contained the source."""
        with self._app.get_db().sessionmaker() as session:
            source = session.get(Character, self.source_id)
            group = CharacterGroup(show_id=self.show_id, name="Ensemble")
            group.characters.append(source)
            session.add(group)
            session.flush()
            group_id = group.id
            session.commit()

        response = self._merge(
            {"source_id": self.source_id, "destination_id": self.destination_id}
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            group = session.get(CharacterGroup, group_id)
            member_ids = [c.id for c in group.characters]
        self.assertIn(self.destination_id, member_ids)
        self.assertNotIn(self.source_id, member_ids)

    def test_merge_group_deduplication(self):
        """Merge does not create a duplicate when destination is already in the group."""
        with self._app.get_db().sessionmaker() as session:
            source = session.get(Character, self.source_id)
            destination = session.get(Character, self.destination_id)
            group = CharacterGroup(show_id=self.show_id, name="Royalty")
            group.characters.append(source)
            group.characters.append(destination)
            session.add(group)
            session.flush()
            group_id = group.id
            session.commit()

        response = self._merge(
            {"source_id": self.source_id, "destination_id": self.destination_id}
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            group = session.get(CharacterGroup, group_id)
            member_ids = [c.id for c in group.characters]
        self.assertEqual(1, len(member_ids))
        self.assertIn(self.destination_id, member_ids)

    def test_merge_deletes_mic_allocations(self):
        """Merge deletes all mic allocations belonging to the source character."""
        with self._app.get_db().sessionmaker() as session:
            mic = Microphone(show_id=self.show_id, name="Radio Mic 1")
            session.add(mic)
            session.flush()
            act = Act(show_id=self.show_id, name="Act 1")
            session.add(act)
            session.flush()
            scene = Scene(show_id=self.show_id, act_id=act.id, name="Scene 1")
            session.add(scene)
            session.flush()
            alloc = MicrophoneAllocation(
                mic_id=mic.id,
                scene_id=scene.id,
                character_id=self.source_id,
            )
            session.add(alloc)
            session.commit()

        response = self._merge(
            {"source_id": self.source_id, "destination_id": self.destination_id}
        )
        self.assertEqual(200, response.code)

        with self._app.get_db().sessionmaker() as session:
            remaining = session.scalars(
                select(MicrophoneAllocation).where(
                    MicrophoneAllocation.character_id == self.source_id
                )
            ).all()
        self.assertEqual(0, len(remaining))
