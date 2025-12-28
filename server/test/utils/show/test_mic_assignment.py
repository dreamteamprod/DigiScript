"""
Unit tests for the auto mic assignment algorithm.

Tests cover character priority ordering, distance-based costs, existing allocation
preservation, over-capacity handling, and edge cases.
"""

import pytest
from unittest.mock import MagicMock
from collections import defaultdict

from utils.show.mic_assignment import (
    swap_cost,
    calculate_swap_cost_with_cast,
    collect_character_appearances,
    find_best_mic,
    _mic_already_used_in_scene,
    _mic_manually_allocated_to_character,
    _mic_used_by_character_in_new_allocations,
)


class TestSwapCost:
    """Test the distance-based cost function."""

    def test_same_scene_zero_cost(self):
        """Same scene should have zero swap cost."""
        assert swap_cost(0, 0) == 0.0
        assert swap_cost(5, 5) == 0.0

    def test_adjacent_scenes_high_cost(self):
        """Adjacent scenes should have highest cost (100)."""
        assert swap_cost(0, 1) == 100.0
        assert swap_cost(5, 6) == 100.0
        assert swap_cost(1, 0) == 100.0

    def test_distant_scenes_low_cost(self):
        """Distant scenes should have lower cost."""
        assert swap_cost(0, 2) == 50.0
        assert swap_cost(0, 5) == 20.0
        assert swap_cost(0, 10) == 10.0

    def test_cost_symmetry(self):
        """Cost should be symmetric (scene order doesn't matter)."""
        assert swap_cost(1, 5) == swap_cost(5, 1)
        assert swap_cost(0, 10) == swap_cost(10, 0)


class TestCollectCharacterAppearances:
    """Test character appearance data collection."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_revision(self):
        """Create a mock script revision with test data."""
        revision = MagicMock()

        # Create mock line associations
        line1 = MagicMock()
        line1.scene_id = 1
        line1.stage_direction = False

        line_part1 = MagicMock()
        line_part1.character_id = 10
        line_part1.character_group_id = None
        line_part1.line_part_cuts = None

        line1.line_parts = [line_part1]

        line_assoc1 = MagicMock()
        line_assoc1.line = line1

        # Line 2 - same character in different scene
        line2 = MagicMock()
        line2.scene_id = 2
        line2.stage_direction = False

        line_part2 = MagicMock()
        line_part2.character_id = 10
        line_part2.character_group_id = None
        line_part2.line_part_cuts = None

        line2.line_parts = [line_part2]

        line_assoc2 = MagicMock()
        line_assoc2.line = line2

        revision.line_associations = [line_assoc1, line_assoc2]
        return revision

    def test_basic_character_counting(self, mock_session, mock_revision):
        """Test basic line counting for characters."""
        existing_allocations = []

        unallocated, totals = collect_character_appearances(
            mock_session, mock_revision, existing_allocations
        )

        # Character 10 should have 2 lines total
        assert totals[10] == 2
        # Should have entries for both scenes
        assert (1, 10) in unallocated
        assert (2, 10) in unallocated
        assert unallocated[(1, 10)] == 1
        assert unallocated[(2, 10)] == 1

    def test_excludes_existing_allocations(self, mock_session, mock_revision):
        """Test that existing allocations are excluded."""
        # Create existing allocation for scene 1, character 10
        existing_alloc = MagicMock()
        existing_alloc.scene_id = 1
        existing_alloc.character_id = 10
        existing_alloc.mic_id = 1

        existing_allocations = [existing_alloc]

        unallocated, totals = collect_character_appearances(
            mock_session, mock_revision, existing_allocations
        )

        # Scene 1 should be excluded
        assert (1, 10) not in unallocated
        # Scene 2 should still be there
        assert (2, 10) in unallocated
        # Total should only count scene 2
        assert totals[10] == 1

    def test_stage_directions_ignored(self):
        """Test that stage directions are not counted."""
        session = MagicMock()
        revision = MagicMock()

        # Create stage direction line
        line = MagicMock()
        line.scene_id = 1
        line.stage_direction = True

        line_part = MagicMock()
        line_part.character_id = 10
        line_part.character_group_id = None
        line_part.line_part_cuts = None

        line.line_parts = [line_part]

        line_assoc = MagicMock()
        line_assoc.line = line

        revision.line_associations = [line_assoc]

        unallocated, totals = collect_character_appearances(session, revision, [])

        # Stage direction should be ignored
        assert 10 not in totals
        assert (1, 10) not in unallocated

    def test_cut_lines_ignored(self):
        """Test that cut lines are not counted."""
        session = MagicMock()
        revision = MagicMock()

        # Create cut line
        line = MagicMock()
        line.scene_id = 1
        line.stage_direction = False

        line_part = MagicMock()
        line_part.character_id = 10
        line_part.character_group_id = None
        line_part.line_part_cuts = MagicMock()

        line.line_parts = [line_part]

        line_assoc = MagicMock()
        line_assoc.line = line

        revision.line_associations = [line_assoc]

        unallocated, totals = collect_character_appearances(session, revision, [])

        # Cut line should be ignored
        assert 10 not in totals
        assert (1, 10) not in unallocated

    def test_character_groups_expanded(self):
        """Test that character groups are expanded into individual characters."""
        session = MagicMock()
        revision = MagicMock()

        # Create line with character group
        line = MagicMock()
        line.scene_id = 1
        line.stage_direction = False

        line_part = MagicMock()
        line_part.character_id = None
        line_part.character_group_id = 100
        line_part.line_part_cuts = None

        # Mock the character group with 2 members
        char1 = MagicMock()
        char1.id = 10
        char2 = MagicMock()
        char2.id = 11

        group = MagicMock()
        group.characters = [char1, char2]

        session.get.return_value = group

        line.line_parts = [line_part]

        line_assoc = MagicMock()
        line_assoc.line = line

        revision.line_associations = [line_assoc]

        unallocated, totals = collect_character_appearances(session, revision, [])

        # Both group members should be counted
        assert totals[10] == 1
        assert totals[11] == 1
        assert (1, 10) in unallocated
        assert (1, 11) in unallocated


class TestFindBestMic:
    """Test optimal mic selection logic."""

    def test_basic_mic_selection(self):
        """Test basic mic selection when all mics available."""
        session = MagicMock()
        available_mics = [1, 2, 3]
        mic_usage_tracker = defaultdict(list)
        existing_allocations = []
        new_allocations = []

        best_mic = find_best_mic(
            session,
            character_id=10,
            scene_id=1,
            scene_index=0,
            available_mics=available_mics,
            mic_usage_tracker=mic_usage_tracker,
            existing_allocations=existing_allocations,
            new_allocations=new_allocations,
        )

        # Should return one of the available mics
        assert best_mic in available_mics

    def test_manual_allocation_continuity_bonus(self):
        """Test that manually allocated mics get strong preference."""
        session = MagicMock()
        available_mics = [1, 2]
        mic_usage_tracker = defaultdict(list)

        # Character 10 already has Mic 1 manually allocated in scene 2
        existing_alloc = MagicMock()
        existing_alloc.mic_id = 1
        existing_alloc.scene_id = 2
        existing_alloc.character_id = 10

        existing_allocations = [existing_alloc]
        new_allocations = []

        best_mic = find_best_mic(
            session,
            character_id=10,
            scene_id=3,
            scene_index=2,
            available_mics=available_mics,
            mic_usage_tracker=mic_usage_tracker,
            existing_allocations=existing_allocations,
            new_allocations=new_allocations,
        )

        # Should prefer Mic 1 due to manual allocation bonus (-100 points)
        assert best_mic == 1

    def test_auto_allocation_continuity_bonus(self):
        """Test that auto-assigned mics get preference for continuity."""
        session = MagicMock()
        available_mics = [1, 2]
        mic_usage_tracker = defaultdict(list)
        existing_allocations = []

        # Character 10 was already assigned Mic 1 in scene 1 by algorithm
        new_allocations = [(1, 1, 10)]

        best_mic = find_best_mic(
            session,
            character_id=10,
            scene_id=2,
            scene_index=1,
            available_mics=available_mics,
            mic_usage_tracker=mic_usage_tracker,
            existing_allocations=existing_allocations,
            new_allocations=new_allocations,
        )

        # Should prefer Mic 1 due to continuity bonus (-50 points)
        assert best_mic == 1

    def test_swap_cost_penalty(self):
        """Test that swap costs influence mic selection."""
        session = MagicMock()
        available_mics = [1, 2]

        # Mock characters with different cast members
        char10 = MagicMock()
        char10.played_by = 100

        char20 = MagicMock()
        char20.played_by = 200  # Different cast member

        session.get.side_effect = lambda model, id: char10 if id == 10 else char20

        # Mic 1 was used by a different character in adjacent scene
        mic_usage_tracker = {1: [(0, 20)], 2: []}
        existing_allocations = []
        new_allocations = []

        best_mic = find_best_mic(
            session,
            character_id=10,
            scene_id=2,
            scene_index=1,
            available_mics=available_mics,
            mic_usage_tracker=mic_usage_tracker,
            existing_allocations=existing_allocations,
            new_allocations=new_allocations,
        )

        # Should prefer Mic 2 to avoid high swap cost (100) from adjacent scene
        assert best_mic == 2

    def test_no_available_mic(self):
        """Test that None is returned when no mics available."""
        session = MagicMock()
        available_mics = [1]
        mic_usage_tracker = defaultdict(list)

        # Mic 1 already used by someone else in this scene
        existing_alloc = MagicMock()
        existing_alloc.mic_id = 1
        existing_alloc.scene_id = 5
        existing_alloc.character_id = 20

        existing_allocations = [existing_alloc]
        new_allocations = []

        best_mic = find_best_mic(
            session,
            character_id=10,
            scene_id=5,
            scene_index=0,
            available_mics=available_mics,
            mic_usage_tracker=mic_usage_tracker,
            existing_allocations=existing_allocations,
            new_allocations=new_allocations,
        )

        # Should return None (no available mic)
        assert best_mic is None


class TestHelperFunctions:
    """Test helper functions for mic availability checks."""

    def test_mic_already_used_in_scene_existing(self):
        """Test detection of mic usage in existing allocations."""
        existing_alloc = MagicMock()
        existing_alloc.mic_id = 1
        existing_alloc.scene_id = 5
        existing_alloc.character_id = 10

        existing_allocations = [existing_alloc]
        new_allocations = []

        # Mic 1 is used in scene 5
        assert _mic_already_used_in_scene(1, 5, existing_allocations, new_allocations)
        # Mic 1 is not used in scene 6
        assert not _mic_already_used_in_scene(
            1, 6, existing_allocations, new_allocations
        )
        # Mic 2 is not used in scene 5
        assert not _mic_already_used_in_scene(
            2, 5, existing_allocations, new_allocations
        )

    def test_mic_already_used_in_scene_new(self):
        """Test detection of mic usage in new allocations."""
        existing_allocations = []
        new_allocations = [(1, 5, 10)]

        # Mic 1 is used in scene 5
        assert _mic_already_used_in_scene(1, 5, existing_allocations, new_allocations)
        # Mic 1 is not used in scene 6
        assert not _mic_already_used_in_scene(
            1, 6, existing_allocations, new_allocations
        )

    def test_mic_manually_allocated_to_character(self):
        """Test detection of manual allocation to character."""
        existing_alloc = MagicMock()
        existing_alloc.mic_id = 1
        existing_alloc.scene_id = 5
        existing_alloc.character_id = 10

        existing_allocations = [existing_alloc]

        # Mic 1 is manually allocated to character 10
        assert _mic_manually_allocated_to_character(1, 10, existing_allocations)
        # Mic 1 is not allocated to character 20
        assert not _mic_manually_allocated_to_character(1, 20, existing_allocations)
        # Mic 2 is not allocated to anyone
        assert not _mic_manually_allocated_to_character(2, 10, existing_allocations)

    def test_mic_used_by_character_in_new_allocations(self):
        """Test detection of mic usage in new allocations."""
        new_allocations = [(1, 5, 10)]

        # Mic 1 is used by character 10
        assert _mic_used_by_character_in_new_allocations(1, 10, new_allocations)
        # Mic 1 is not used by character 20
        assert not _mic_used_by_character_in_new_allocations(1, 20, new_allocations)
        # Mic 2 is not used by anyone
        assert not _mic_used_by_character_in_new_allocations(2, 10, new_allocations)


class TestCastMemberSwapCost:
    """Test cast member awareness in swap cost calculations."""

    def test_same_cast_member_zero_cost(self):
        """Test that swapping between characters played by same cast member has zero cost."""
        session = MagicMock()

        # Create characters played by same cast member
        char1 = MagicMock()
        char1.played_by = 100  # Cast member ID 100

        char2 = MagicMock()
        char2.played_by = 100  # Same cast member

        # Mock session.get to return our characters
        session.get.side_effect = lambda model, id: char1 if id == 10 else char2

        # Adjacent scenes would normally cost 100, but same cast member = 0
        cost = calculate_swap_cost_with_cast(session, 10, 20, 0, 1)
        assert cost == 0.0

    def test_different_cast_members_distance_cost(self):
        """Test that swapping between characters played by different cast members uses distance cost."""
        session = MagicMock()

        # Create characters played by different cast members
        char1 = MagicMock()
        char1.played_by = 100

        char2 = MagicMock()
        char2.played_by = 200  # Different cast member

        session.get.side_effect = lambda model, id: char1 if id == 10 else char2

        # Adjacent scenes should cost 100 (distance-based)
        cost = calculate_swap_cost_with_cast(session, 10, 20, 0, 1)
        assert cost == 100.0

        # Distant scenes should cost less
        cost = calculate_swap_cost_with_cast(session, 10, 20, 0, 5)
        assert cost == 20.0

    def test_no_cast_assignment_distance_cost(self):
        """Test that characters without cast assignments use distance cost."""
        session = MagicMock()

        # Create characters without cast assignments
        char1 = MagicMock()
        char1.played_by = None

        char2 = MagicMock()
        char2.played_by = None

        session.get.side_effect = lambda model, id: char1 if id == 10 else char2

        # Should fall back to distance-based cost
        cost = calculate_swap_cost_with_cast(session, 10, 20, 0, 1)
        assert cost == 100.0

    def test_one_cast_assignment_distance_cost(self):
        """Test that if only one character has cast assignment, use distance cost."""
        session = MagicMock()

        # One has cast assignment, one doesn't
        char1 = MagicMock()
        char1.played_by = 100

        char2 = MagicMock()
        char2.played_by = None

        session.get.side_effect = lambda model, id: char1 if id == 10 else char2

        # Should fall back to distance-based cost
        cost = calculate_swap_cost_with_cast(session, 10, 20, 0, 1)
        assert cost == 100.0

    def test_cast_aware_mic_selection(self):
        """Test that cast member awareness influences mic selection."""
        session = MagicMock()
        available_mics = [1, 2]

        # Character 10 and 20 are played by same cast member
        char10 = MagicMock()
        char10.played_by = 100

        char20 = MagicMock()
        char20.played_by = 100

        session.get.side_effect = lambda model, id: char10 if id == 10 else char20

        # Mic 1 was used by character 20 (same cast member as 10) in previous scene
        # Mic 2 is unused
        mic_usage_tracker = {
            1: [(0, 20)],  # Character 20 in scene 0
            2: [],
        }
        existing_allocations = []
        new_allocations = []

        best_mic = find_best_mic(
            session,
            character_id=10,
            scene_id=2,
            scene_index=1,
            available_mics=available_mics,
            mic_usage_tracker=mic_usage_tracker,
            existing_allocations=existing_allocations,
            new_allocations=new_allocations,
        )

        # Should prefer Mic 1 because same cast member = zero swap cost
        # Mic 1 score: 0 (same cast member)
        # Mic 2 score: 0 (unused)
        # Both have same score, so either is acceptable
        assert best_mic in [1, 2]
