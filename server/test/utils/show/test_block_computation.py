"""Unit tests for block computation utilities."""

from models.show import Scene, Show
from models.stage import (
    CrewAssignment,
    Props,
    PropsAllocation,
    Scenery,
    SceneryAllocation,
)
from test.conftest import DigiScriptTestCase
from test.helpers.stage_fixtures import (
    create_act_with_scenes,
    create_crew,
    create_prop,
    create_scenery,
    create_show,
)
from utils.show.block_computation import (
    Block,
    compute_blocks_for_prop,
    compute_blocks_for_scenery,
    delete_orphaned_assignments_for_prop,
    delete_orphaned_assignments_for_scenery,
    find_orphaned_assignments_for_prop,
    find_orphaned_assignments_for_scenery,
    get_ordered_scenes_by_act,
    is_valid_boundary,
    is_valid_set_boundary,
    is_valid_strike_boundary,
)


class TestGetOrderedScenesByAct(DigiScriptTestCase):
    """Tests for get_ordered_scenes_by_act function."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            self.show_id = create_show(session)
            session.commit()

    def test_empty_show(self):
        """Test with show that has no acts or scenes."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            result = get_ordered_scenes_by_act(show)
            self.assertEqual({}, result)

    def test_single_act_single_scene(self):
        """Test with a single act containing a single scene."""
        with self._app.get_db().sessionmaker() as session:
            act_id, scene_ids = create_act_with_scenes(
                session, self.show_id, "Act 1", 1, link_to_show=True
            )
            session.commit()

            show = session.get(Show, self.show_id)
            result = get_ordered_scenes_by_act(show)

            self.assertEqual(1, len(result))
            self.assertIn(act_id, result)
            self.assertEqual(1, len(result[act_id]))
            self.assertEqual(scene_ids[0], result[act_id][0].id)

    def test_single_act_multiple_scenes(self):
        """Test with a single act containing multiple scenes in linked list order."""
        with self._app.get_db().sessionmaker() as session:
            act_id, scene_ids = create_act_with_scenes(
                session, self.show_id, "Act 1", 3, link_to_show=True
            )
            session.commit()

            show = session.get(Show, self.show_id)
            result = get_ordered_scenes_by_act(show)

            self.assertEqual(1, len(result))
            self.assertEqual(3, len(result[act_id]))
            self.assertEqual("Scene 1", result[act_id][0].name)
            self.assertEqual("Scene 2", result[act_id][1].name)
            self.assertEqual("Scene 3", result[act_id][2].name)

    def test_multiple_acts(self):
        """Test with multiple acts each containing scenes."""
        with self._app.get_db().sessionmaker() as session:
            act1_id, _ = create_act_with_scenes(
                session,
                self.show_id,
                "Act 1",
                2,
                interval_after=True,
                link_to_show=True,
            )
            act2_id, _ = create_act_with_scenes(
                session,
                self.show_id,
                "Act 2",
                1,
                previous_act_id=act1_id,
            )
            session.commit()

            show = session.get(Show, self.show_id)
            result = get_ordered_scenes_by_act(show)

            self.assertEqual(2, len(result))
            self.assertEqual(2, len(result[act1_id]))
            self.assertEqual(1, len(result[act2_id]))


class TestComputeBlocksForProp(DigiScriptTestCase):
    """Tests for compute_blocks_for_prop function."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            self.show_id = create_show(session)
            self.act1_id, scene_ids = create_act_with_scenes(
                session,
                self.show_id,
                "Act 1",
                4,
                interval_after=True,
                link_to_show=True,
            )
            self.scene1_id, self.scene2_id, self.scene3_id, self.scene4_id = scene_ids
            _, self.prop_id = create_prop(session, self.show_id)
            session.commit()

    def test_no_allocations(self):
        """Test prop with no allocations returns empty list."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            blocks = compute_blocks_for_prop(prop, show)
            self.assertEqual([], blocks)

    def test_single_scene_allocation(self):
        """Test single scene allocation creates one block."""
        with self._app.get_db().sessionmaker() as session:
            # Allocate prop to scene 2
            allocation = PropsAllocation(props_id=self.prop_id, scene_id=self.scene2_id)
            session.add(allocation)
            session.commit()

            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            blocks = compute_blocks_for_prop(prop, show)

            self.assertEqual(1, len(blocks))
            self.assertEqual(self.act1_id, blocks[0].act_id)
            self.assertEqual([self.scene2_id], blocks[0].scene_ids)
            self.assertEqual(self.scene2_id, blocks[0].set_scene_id)
            self.assertEqual(self.scene2_id, blocks[0].strike_scene_id)
            self.assertTrue(blocks[0].is_single_scene)

    def test_consecutive_scenes(self):
        """Test consecutive scene allocations form one block."""
        with self._app.get_db().sessionmaker() as session:
            # Allocate prop to scenes 2 and 3
            allocation1 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene2_id
            )
            allocation2 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene3_id
            )
            session.add_all([allocation1, allocation2])
            session.commit()

            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            blocks = compute_blocks_for_prop(prop, show)

            self.assertEqual(1, len(blocks))
            self.assertEqual([self.scene2_id, self.scene3_id], blocks[0].scene_ids)
            self.assertEqual(self.scene2_id, blocks[0].set_scene_id)
            self.assertEqual(self.scene3_id, blocks[0].strike_scene_id)
            self.assertFalse(blocks[0].is_single_scene)

    def test_gap_creates_separate_blocks(self):
        """Test gap between allocations creates separate blocks."""
        with self._app.get_db().sessionmaker() as session:
            # Allocate prop to scenes 1 and 3 (gap at scene 2)
            allocation1 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene1_id
            )
            allocation2 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene3_id
            )
            session.add_all([allocation1, allocation2])
            session.commit()

            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            blocks = compute_blocks_for_prop(prop, show)

            self.assertEqual(2, len(blocks))

            # First block: scene 1
            self.assertEqual([self.scene1_id], blocks[0].scene_ids)
            self.assertEqual(self.scene1_id, blocks[0].set_scene_id)
            self.assertEqual(self.scene1_id, blocks[0].strike_scene_id)

            # Second block: scene 3
            self.assertEqual([self.scene3_id], blocks[1].scene_ids)
            self.assertEqual(self.scene3_id, blocks[1].set_scene_id)
            self.assertEqual(self.scene3_id, blocks[1].strike_scene_id)

    def test_all_scenes_allocated(self):
        """Test all scenes allocated forms one block."""
        with self._app.get_db().sessionmaker() as session:
            for scene_id in [
                self.scene1_id,
                self.scene2_id,
                self.scene3_id,
                self.scene4_id,
            ]:
                allocation = PropsAllocation(props_id=self.prop_id, scene_id=scene_id)
                session.add(allocation)
            session.commit()

            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            blocks = compute_blocks_for_prop(prop, show)

            self.assertEqual(1, len(blocks))
            self.assertEqual(
                [self.scene1_id, self.scene2_id, self.scene3_id, self.scene4_id],
                blocks[0].scene_ids,
            )

    def test_act_boundary_breaks_blocks(self):
        """Test allocations in different acts create separate blocks."""
        with self._app.get_db().sessionmaker() as session:
            # Create Act 2 with a scene
            act2_id, act2_scene_ids = create_act_with_scenes(
                session,
                self.show_id,
                "Act 2",
                1,
                previous_act_id=self.act1_id,
            )

            # Allocate prop to last scene of Act 1 and first scene of Act 2
            allocation1 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene4_id
            )
            allocation2 = PropsAllocation(
                props_id=self.prop_id, scene_id=act2_scene_ids[0]
            )
            session.add_all([allocation1, allocation2])
            session.commit()

            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            blocks = compute_blocks_for_prop(prop, show)

            # Should be 2 blocks, one per act
            self.assertEqual(2, len(blocks))
            self.assertEqual(self.act1_id, blocks[0].act_id)
            self.assertEqual(act2_id, blocks[1].act_id)


class TestComputeBlocksForScenery(DigiScriptTestCase):
    """Tests for compute_blocks_for_scenery function."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            self.show_id = create_show(session)
            self.act1_id, scene_ids = create_act_with_scenes(
                session,
                self.show_id,
                "Act 1",
                3,
                link_to_show=True,
            )
            self.scene1_id, self.scene2_id, self.scene3_id = scene_ids
            _, self.scenery_id = create_scenery(session, self.show_id)
            session.commit()

    def test_no_allocations(self):
        """Test scenery with no allocations returns empty list."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            scenery = session.get(Scenery, self.scenery_id)
            blocks = compute_blocks_for_scenery(scenery, show)
            self.assertEqual([], blocks)

    def test_consecutive_scenes(self):
        """Test consecutive scene allocations for scenery form one block."""
        with self._app.get_db().sessionmaker() as session:
            allocation1 = SceneryAllocation(
                scenery_id=self.scenery_id, scene_id=self.scene1_id
            )
            allocation2 = SceneryAllocation(
                scenery_id=self.scenery_id, scene_id=self.scene2_id
            )
            session.add_all([allocation1, allocation2])
            session.commit()

            show = session.get(Show, self.show_id)
            scenery = session.get(Scenery, self.scenery_id)
            blocks = compute_blocks_for_scenery(scenery, show)

            self.assertEqual(1, len(blocks))
            self.assertEqual([self.scene1_id, self.scene2_id], blocks[0].scene_ids)
            self.assertEqual(self.scene1_id, blocks[0].set_scene_id)
            self.assertEqual(self.scene2_id, blocks[0].strike_scene_id)


class TestBoundaryValidation(DigiScriptTestCase):
    """Tests for boundary validation functions."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            self.show_id = create_show(session)
            self.act_id, scene_ids = create_act_with_scenes(
                session,
                self.show_id,
                "Act 1",
                3,
                link_to_show=True,
            )
            self.scene1_id, self.scene2_id, self.scene3_id = scene_ids
            _, self.prop_id = create_prop(session, self.show_id)

            # Allocate prop to scenes 1 and 2 (forms one block)
            allocation1 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene1_id
            )
            allocation2 = PropsAllocation(
                props_id=self.prop_id, scene_id=self.scene2_id
            )
            session.add_all([allocation1, allocation2])
            session.commit()

    def test_is_valid_set_boundary_first_scene(self):
        """Test first scene of block is valid SET boundary."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            result = is_valid_set_boundary(
                session, self.scene1_id, self.prop_id, None, show
            )
            self.assertTrue(result)

    def test_is_valid_set_boundary_middle_scene(self):
        """Test middle scene of block is NOT valid SET boundary."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            result = is_valid_set_boundary(
                session, self.scene2_id, self.prop_id, None, show
            )
            self.assertFalse(result)

    def test_is_valid_strike_boundary_last_scene(self):
        """Test last scene of block is valid STRIKE boundary."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            result = is_valid_strike_boundary(
                session, self.scene2_id, self.prop_id, None, show
            )
            self.assertTrue(result)

    def test_is_valid_strike_boundary_first_scene(self):
        """Test first scene of multi-scene block is NOT valid STRIKE boundary."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            result = is_valid_strike_boundary(
                session, self.scene1_id, self.prop_id, None, show
            )
            self.assertFalse(result)

    def test_is_valid_boundary_unallocated_scene(self):
        """Test unallocated scene is not valid for any boundary type."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)

            # Scene 3 is not allocated
            set_result = is_valid_set_boundary(
                session, self.scene3_id, self.prop_id, None, show
            )
            strike_result = is_valid_strike_boundary(
                session, self.scene3_id, self.prop_id, None, show
            )

            self.assertFalse(set_result)
            self.assertFalse(strike_result)

    def test_is_valid_boundary_single_scene_block(self):
        """Test single-scene block is valid for both SET and STRIKE."""
        # Add a 4th scene and allocate to only scene 4 (gap at scene 3)
        # This creates: Block 1 (scenes 1-2), gap at 3, Block 2 (scene 4 only)
        with self._app.get_db().sessionmaker() as session:
            # Add scene 4
            scene4 = Scene(
                show_id=self.show_id,
                act_id=self.act_id,
                name="Scene 4",
                previous_scene_id=self.scene3_id,
            )
            session.add(scene4)
            session.flush()
            scene4_id = scene4.id

            # Allocate prop to scene 4 (gap at scene 3 creates separate block)
            allocation = PropsAllocation(props_id=self.prop_id, scene_id=scene4_id)
            session.add(allocation)
            session.commit()

        # Use fresh session to ensure allocation is loaded
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)

            # Verify the allocations exist in the fresh session
            blocks = compute_blocks_for_prop(prop, show)
            # Should have 2 blocks: scenes 1-2 and scene 4
            self.assertEqual(2, len(blocks))

            # Scene 4 should be both SET and STRIKE for its single-scene block
            set_result = is_valid_set_boundary(
                session, scene4_id, self.prop_id, None, show
            )
            strike_result = is_valid_strike_boundary(
                session, scene4_id, self.prop_id, None, show
            )

            self.assertTrue(set_result)
            self.assertTrue(strike_result)

    def test_is_valid_boundary_generic_function(self):
        """Test is_valid_boundary dispatches correctly based on assignment_type."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)

            # Scene 1 is valid SET, not valid STRIKE
            set_result = is_valid_boundary(
                session, self.scene1_id, "set", self.prop_id, None, show
            )
            strike_result = is_valid_boundary(
                session, self.scene1_id, "strike", self.prop_id, None, show
            )

            self.assertTrue(set_result)
            self.assertFalse(strike_result)

            # Scene 2 is valid STRIKE, not valid SET
            set_result = is_valid_boundary(
                session, self.scene2_id, "set", self.prop_id, None, show
            )
            strike_result = is_valid_boundary(
                session, self.scene2_id, "strike", self.prop_id, None, show
            )

            self.assertFalse(set_result)
            self.assertTrue(strike_result)

    def test_is_valid_boundary_invalid_type(self):
        """Test is_valid_boundary returns False for invalid assignment_type."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            result = is_valid_boundary(
                session, self.scene1_id, "invalid", self.prop_id, None, show
            )
            self.assertFalse(result)

    def test_is_valid_boundary_nonexistent_prop(self):
        """Test boundary check for non-existent prop returns False."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            result = is_valid_boundary(
                session, self.scene1_id, "set", 99999, None, show
            )
            self.assertFalse(result)


class TestOrphanDetection(DigiScriptTestCase):
    """Tests for orphaned crew assignment detection and deletion."""

    def setUp(self):
        super().setUp()
        with self._app.get_db().sessionmaker() as session:
            self.show_id = create_show(session)
            self.act_id, scene_ids = create_act_with_scenes(
                session,
                self.show_id,
                "Act 1",
                4,
                link_to_show=True,
            )
            (
                self.scene1_id,
                self.scene2_id,
                self.scene3_id,
                self.scene4_id,
            ) = scene_ids
            self.crew_id = create_crew(session, self.show_id)
            _, self.prop_id = create_prop(session, self.show_id)

            # Initial allocation: scenes 1, 2, 3 (one block)
            # SET boundary: scene 1, STRIKE boundary: scene 3
            for scene_id in [self.scene1_id, self.scene2_id, self.scene3_id]:
                allocation = PropsAllocation(props_id=self.prop_id, scene_id=scene_id)
                session.add(allocation)

            session.commit()

    def test_find_orphaned_no_assignments(self):
        """Test find_orphaned returns empty when no assignments exist."""
        with self._app.get_db().sessionmaker() as session:
            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            orphaned = find_orphaned_assignments_for_prop(session, prop, show)
            self.assertEqual([], orphaned)

    def test_find_orphaned_valid_assignments(self):
        """Test find_orphaned returns empty for valid assignments."""
        with self._app.get_db().sessionmaker() as session:
            # Create valid assignments
            set_assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene1_id,  # Valid SET boundary
                assignment_type="set",
                prop_id=self.prop_id,
            )
            strike_assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene3_id,  # Valid STRIKE boundary
                assignment_type="strike",
                prop_id=self.prop_id,
            )
            session.add_all([set_assignment, strike_assignment])
            session.commit()

            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            orphaned = find_orphaned_assignments_for_prop(session, prop, show)
            self.assertEqual([], orphaned)

    def test_find_orphaned_after_allocation_change(self):
        """Test find_orphaned detects assignments that become invalid."""
        with self._app.get_db().sessionmaker() as session:
            # Create assignment at scene 3 STRIKE
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene3_id,
                assignment_type="strike",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.commit()
            assignment_id = assignment.id

            # Now remove scene 3 allocation (making scene 2 the new STRIKE boundary)
            scene3_allocation = (
                session.query(PropsAllocation)
                .filter_by(props_id=self.prop_id, scene_id=self.scene3_id)
                .first()
            )
            session.delete(scene3_allocation)
            session.commit()

            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            session.refresh(prop)  # Refresh to get updated allocations
            orphaned = find_orphaned_assignments_for_prop(session, prop, show)

            self.assertEqual(1, len(orphaned))
            self.assertEqual(assignment_id, orphaned[0].id)

    def test_delete_orphaned_assignments(self):
        """Test delete_orphaned actually removes orphaned assignments."""
        with self._app.get_db().sessionmaker() as session:
            # Create assignment at scene 3 STRIKE
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene3_id,
                assignment_type="strike",
                prop_id=self.prop_id,
            )
            session.add(assignment)
            session.commit()
            assignment_id = assignment.id

            # Remove scene 3 allocation
            scene3_allocation = (
                session.query(PropsAllocation)
                .filter_by(props_id=self.prop_id, scene_id=self.scene3_id)
                .first()
            )
            session.delete(scene3_allocation)
            session.commit()

            show = session.get(Show, self.show_id)
            prop = session.get(Props, self.prop_id)
            session.refresh(prop)

            deleted_ids = delete_orphaned_assignments_for_prop(session, prop, show)
            session.commit()

            self.assertEqual([assignment_id], deleted_ids)

            # Verify assignment is deleted
            assignment = session.get(CrewAssignment, assignment_id)
            self.assertIsNone(assignment)

    def test_find_orphaned_for_scenery(self):
        """Test orphan detection works for scenery items."""
        with self._app.get_db().sessionmaker() as session:
            _, scenery_id = create_scenery(session, self.show_id)

            # Allocate to scenes 1 and 2
            allocation1 = SceneryAllocation(
                scenery_id=scenery_id, scene_id=self.scene1_id
            )
            allocation2 = SceneryAllocation(
                scenery_id=scenery_id, scene_id=self.scene2_id
            )
            session.add_all([allocation1, allocation2])

            # Create assignment at scene 2 STRIKE
            assignment = CrewAssignment(
                crew_id=self.crew_id,
                scene_id=self.scene2_id,
                assignment_type="strike",
                scenery_id=scenery_id,
            )
            session.add(assignment)
            session.commit()
            assignment_id = assignment.id

            # Remove scene 2 allocation (making scene 1 both SET and STRIKE)
            scene2_allocation = (
                session.query(SceneryAllocation)
                .filter_by(scenery_id=scenery_id, scene_id=self.scene2_id)
                .first()
            )
            session.delete(scene2_allocation)
            session.commit()

            show = session.get(Show, self.show_id)
            scenery = session.get(Scenery, scenery_id)
            session.refresh(scenery)

            orphaned = find_orphaned_assignments_for_scenery(session, scenery, show)
            self.assertEqual(1, len(orphaned))
            self.assertEqual(assignment_id, orphaned[0].id)

            # Test deletion
            deleted_ids = delete_orphaned_assignments_for_scenery(
                session, scenery, show
            )
            self.assertEqual([assignment_id], deleted_ids)


class TestBlockDataclass(DigiScriptTestCase):
    """Tests for Block dataclass."""

    def test_is_single_scene_true(self):
        """Test is_single_scene returns True for single-scene blocks."""
        block = Block(act_id=1, scene_ids=[10], set_scene_id=10, strike_scene_id=10)
        self.assertTrue(block.is_single_scene)

    def test_is_single_scene_false(self):
        """Test is_single_scene returns False for multi-scene blocks."""
        block = Block(
            act_id=1, scene_ids=[10, 11, 12], set_scene_id=10, strike_scene_id=12
        )
        self.assertFalse(block.is_single_scene)
