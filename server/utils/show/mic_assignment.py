"""
Auto mic assignment algorithm.

This module implements a character-first holistic approach to assigning microphones
to characters across scenes, minimizing the cost of mic swaps with a distance-based
cost function.
"""

from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from models.mics import MicrophoneAllocation
from models.script import ScriptLine, ScriptRevision
from models.show import Character, CharacterGroup


def swap_cost(scene_index_1: int, scene_index_2: int) -> float:
    """
    Calculate the cost of swapping a mic between two scenes.

    Inverted distance cost: closer scenes = HIGHER cost.
    Encourages mic sharing across non-adjacent scenes.

    :param scene_index_1: Index of first scene in the scene group
    :param scene_index_2: Index of second scene in the scene group
    :return: Cost value (0-100). Adjacent scenes (distance=1) cost 100.0,
             distant scenes cost less (e.g., distance=5 costs 20.0).
    """
    distance = abs(scene_index_1 - scene_index_2)
    if distance == 0:
        return 0.0  # Same scene = free
    return 100.0 / distance


def calculate_swap_cost_with_cast(
    session: Session,
    character_id_1: int,
    character_id_2: int,
    scene_index_1: int,
    scene_index_2: int,
) -> float:
    """
    Calculate swap cost considering cast member assignments.

    If both characters are played by the same cast member, the swap cost is ZERO
    because the mic physically stays on the same person. Otherwise, uses distance-based cost.

    :param session: SQLAlchemy session for querying cast assignments
    :param character_id_1: First character ID
    :param character_id_2: Second character ID
    :param scene_index_1: Scene index for first character
    :param scene_index_2: Scene index for second character
    :return: Swap cost (0 if same cast member, distance-based otherwise)
    """
    # Get cast assignments for both characters
    char1: Character = session.get(Character, character_id_1)
    char2: Character = session.get(Character, character_id_2)

    # If both characters have cast assignments and they're the same person
    if char1 and char2 and char1.played_by and char2.played_by:
        if char1.played_by == char2.played_by:
            # Same cast member = zero cost (mic stays on same person)
            return 0.0

    # Different cast members (or no cast assignment) = distance-based cost
    return swap_cost(scene_index_1, scene_index_2)


def collect_character_appearances(
    session: Session,
    revision: ScriptRevision,
    existing_allocations: List[MicrophoneAllocation],
) -> Tuple[Dict[Tuple[int, int], int], Dict[int, int]]:
    """
    Query database to build character appearance data for unallocated (character, scene) pairs.

    This function examines all script lines in each scene, counts non-cut lines per character,
    and excludes any pairs that already have manual allocations.

    :param session: SQLAlchemy session
    :param revision: Current script revision to check for cuts
    :param existing_allocations: List of existing MicrophoneAllocation objects
    :return: Tuple of (unallocated_appearances, character_total_lines) where unallocated_appearances maps (scene_id, character_id) to line_count and character_total_lines maps character_id to total_line_count
    """
    unallocated_appearances: Dict[Tuple[int, int], int] = {}
    character_total_lines: Dict[int, int] = defaultdict(int)

    # Build set of already-allocated (scene, character) pairs for quick lookup
    allocated_pairs = {
        (alloc.scene_id, alloc.character_id) for alloc in existing_allocations
    }

    # Process all lines in the revision
    for line_assoc in revision.line_associations:
        line: ScriptLine = line_assoc.line

        # Skip stage directions
        if line.stage_direction:
            continue

        # Count lines per character
        for line_part in line.line_parts:
            # Skip cut lines
            if line_part.line_part_cuts is not None:
                continue

            # Get character IDs (expand groups)
            character_ids = []
            if line_part.character_id:
                character_ids.append(line_part.character_id)
            elif line_part.character_group_id:
                group: CharacterGroup = session.get(
                    CharacterGroup, line_part.character_group_id
                )
                if group:
                    character_ids.extend([char.id for char in group.characters])

            # Count lines for each character
            for character_id in character_ids:
                # Skip if this (scene, character) pair already has a manual allocation
                if (line.scene_id, character_id) in allocated_pairs:
                    continue

                # Track this appearance
                key = (line.scene_id, character_id)
                unallocated_appearances[key] = unallocated_appearances.get(key, 0) + 1

                # Track total lines per character
                character_total_lines[character_id] += 1

    return unallocated_appearances, dict(character_total_lines)


def find_best_mic(
    session: Session,
    character_id: int,
    scene_id: int,
    scene_index: int,
    available_mics: List[int],
    mic_usage_tracker: Dict[int, List[Tuple[int, int]]],
    existing_allocations: List[MicrophoneAllocation],
    new_allocations: List[Tuple[int, int, int]],
) -> Optional[int]:
    """
    Find the best microphone for a character in a specific scene.

    Uses scoring criteria to select the optimal mic, preferring continuity and
    minimizing swap costs. Considers cast member assignments to eliminate swap
    costs when the same person plays multiple characters.

    :param session: SQLAlchemy session for querying cast assignments
    :param character_id: ID of the character needing a mic
    :param scene_id: ID of the scene
    :param scene_index: Index of the scene within its scene group
    :param available_mics: List of available microphone IDs
    :param mic_usage_tracker: Dict mapping mic_id to list of (scene_index, character_id) tuples
    :param existing_allocations: List of existing manual allocations
    :param new_allocations: List of (mic_id, scene_id, character_id) tuples for new allocations
    :return: Best microphone ID, or None if no mic available
    """
    best_mic: Optional[int] = None
    best_score = float("inf")

    for mic_id in available_mics:
        # Skip if mic already assigned to someone else in THIS scene
        if _mic_already_used_in_scene(
            mic_id, scene_id, existing_allocations, new_allocations
        ):
            continue

        # Calculate score for this mic
        score = 0.0

        # STRONG BONUS: Existing manual allocation uses this mic for this character
        if _mic_manually_allocated_to_character(
            mic_id, character_id, existing_allocations
        ):
            score -= 100.0

        # BONUS: Algorithm already assigned this mic to this character in earlier scene
        if _mic_used_by_character_in_new_allocations(
            mic_id, character_id, new_allocations
        ):
            score -= 50.0

        # PENALTY: Swap costs from existing and new allocations (considering cast assignments)
        if mic_id in mic_usage_tracker:
            for prev_scene_idx, prev_char_id in mic_usage_tracker[mic_id]:
                if prev_char_id != character_id:
                    # Different character used this mic - calculate swap cost with cast awareness
                    score += calculate_swap_cost_with_cast(
                        session, prev_char_id, character_id, prev_scene_idx, scene_index
                    )

        if score < best_score:
            best_score = score
            best_mic = mic_id

    return best_mic


def _mic_already_used_in_scene(
    mic_id: int,
    scene_id: int,
    existing_allocations: List[MicrophoneAllocation],
    new_allocations: List[Tuple[int, int, int]],
) -> bool:
    """
    Check if a mic is already assigned to someone in a specific scene.

    :param mic_id: Microphone ID
    :param scene_id: Scene ID
    :param existing_allocations: List of existing manual allocations
    :param new_allocations: List of (mic_id, scene_id, character_id) tuples
    :return: True if mic is already used in this scene
    """
    # Check existing allocations
    for alloc in existing_allocations:
        if alloc.mic_id == mic_id and alloc.scene_id == scene_id:
            return True

    # Check new allocations
    for new_mic_id, new_scene_id, _ in new_allocations:
        if new_mic_id == mic_id and new_scene_id == scene_id:
            return True

    return False


def _mic_manually_allocated_to_character(
    mic_id: int, character_id: int, existing_allocations: List[MicrophoneAllocation]
) -> bool:
    """
    Check if a mic is manually allocated to a character in any scene.

    :param mic_id: Microphone ID
    :param character_id: Character ID
    :param existing_allocations: List of existing manual allocations
    :return: True if mic is manually assigned to this character anywhere
    """
    for alloc in existing_allocations:
        if alloc.mic_id == mic_id and alloc.character_id == character_id:
            return True
    return False


def _mic_used_by_character_in_new_allocations(
    mic_id: int, character_id: int, new_allocations: List[Tuple[int, int, int]]
) -> bool:
    """
    Check if a mic has been assigned to a character in new allocations.

    :param mic_id: Microphone ID
    :param character_id: Character ID
    :param new_allocations: List of (mic_id, scene_id, character_id) tuples
    :return: True if mic is assigned to this character in new allocations
    """
    for new_mic_id, _, new_char_id in new_allocations:
        if new_mic_id == mic_id and new_char_id == character_id:
            return True
    return False
