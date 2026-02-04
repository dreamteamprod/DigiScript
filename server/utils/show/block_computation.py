"""
Utility functions for computing allocation blocks from scene-by-scene allocations.

A "block" is a consecutive sequence of scenes where an item (prop or scenery) is allocated.
Blocks are computed per-act and never span act boundaries.

For each block:
- The first scene is the SET boundary (where the item is brought on stage)
- The last scene is the STRIKE boundary (where the item is removed)
- Single-scene blocks have both SET and STRIKE on the same scene
"""

from dataclasses import dataclass
from typing import List, Set

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.show import Scene, Show
from models.stage import CrewAssignment, Props, Scenery


@dataclass
class Block:
    """
    Represents a consecutive allocation block for an item within an act.

    :param act_id: ID of the act containing this block
    :param scene_ids: List of scene IDs in this block, in order
    :param set_scene_id: ID of the scene where the item is SET (first scene)
    :param strike_scene_id: ID of the scene where the item is STRUCK (last scene)
    """

    act_id: int
    scene_ids: List[int]
    set_scene_id: int
    strike_scene_id: int

    @property
    def is_single_scene(self) -> bool:
        """Return True if this block contains only one scene."""
        return len(self.scene_ids) == 1


def get_ordered_scenes_by_act(show: Show) -> dict[int, List[Scene]]:
    """
    Get all scenes in a show, grouped by act and ordered within each act.

    :param show: The show to get scenes for
    :returns: Dictionary mapping act_id to list of scenes in order
    """
    result: dict[int, List[Scene]] = {}

    # Traverse acts in order via linked list
    act = show.first_act
    while act:
        scenes = []
        scene = act.first_scene
        while scene:
            scenes.append(scene)
            scene = scene.next_scene
        if scenes:
            result[act.id] = scenes
        act = act.next_act

    return result


def compute_blocks_for_prop(prop: Props, show: Show) -> List[Block]:
    """
    Compute allocation blocks for a prop.

    :param prop: The prop to compute blocks for
    :param show: The show containing the prop
    :returns: List of Block objects representing consecutive allocations
    """
    # Get all scene IDs where this prop is allocated
    allocated_scene_ids: Set[int] = {
        alloc.scene_id for alloc in prop.scene_allocations
    }

    return _compute_blocks(show, allocated_scene_ids)


def compute_blocks_for_scenery(scenery: Scenery, show: Show) -> List[Block]:
    """
    Compute allocation blocks for a scenery item.

    :param scenery: The scenery item to compute blocks for
    :param show: The show containing the scenery
    :returns: List of Block objects representing consecutive allocations
    """
    # Get all scene IDs where this scenery is allocated
    allocated_scene_ids: Set[int] = {
        alloc.scene_id for alloc in scenery.scene_allocations
    }

    return _compute_blocks(show, allocated_scene_ids)


def _compute_blocks(show: Show, allocated_scene_ids: Set[int]) -> List[Block]:
    """
    Internal function to compute blocks from a set of allocated scene IDs.

    :param show: The show to compute blocks for
    :param allocated_scene_ids: Set of scene IDs where the item is allocated
    :returns: List of Block objects
    """
    if not allocated_scene_ids:
        return []

    blocks: List[Block] = []
    ordered_scenes_by_act = get_ordered_scenes_by_act(show)

    for act_id, scenes in ordered_scenes_by_act.items():
        current_block_scenes: List[int] = []

        for scene in scenes:
            if scene.id in allocated_scene_ids:
                # Scene is allocated - add to current block
                current_block_scenes.append(scene.id)
            # Scene is not allocated - end current block if one exists
            elif current_block_scenes:
                blocks.append(
                    Block(
                        act_id=act_id,
                        scene_ids=current_block_scenes.copy(),
                        set_scene_id=current_block_scenes[0],
                        strike_scene_id=current_block_scenes[-1],
                    )
                )
                current_block_scenes = []

        # Don't forget the last block in the act
        if current_block_scenes:
            blocks.append(
                Block(
                    act_id=act_id,
                    scene_ids=current_block_scenes.copy(),
                    set_scene_id=current_block_scenes[0],
                    strike_scene_id=current_block_scenes[-1],
                )
            )

    return blocks


def is_valid_set_boundary(
    session: Session,
    scene_id: int,
    prop_id: int | None,
    scenery_id: int | None,
    show: Show,
) -> bool:
    """
    Check if a scene is a valid SET boundary for an item.

    A scene is a valid SET boundary if it's the first scene of a block
    (i.e., the item is allocated to this scene and either it's the first
    scene in the act or the previous scene doesn't have the item allocated).

    :param session: Database session
    :param scene_id: Scene ID to check
    :param prop_id: Prop ID (if checking a prop)
    :param scenery_id: Scenery ID (if checking scenery)
    :param show: The show
    :returns: True if the scene is a valid SET boundary
    """
    if prop_id is not None:
        prop = session.get(Props, prop_id)
        if not prop:
            return False
        blocks = compute_blocks_for_prop(prop, show)
    elif scenery_id is not None:
        scenery = session.get(Scenery, scenery_id)
        if not scenery:
            return False
        blocks = compute_blocks_for_scenery(scenery, show)
    else:
        return False

    return any(block.set_scene_id == scene_id for block in blocks)


def is_valid_strike_boundary(
    session: Session,
    scene_id: int,
    prop_id: int | None,
    scenery_id: int | None,
    show: Show,
) -> bool:
    """
    Check if a scene is a valid STRIKE boundary for an item.

    A scene is a valid STRIKE boundary if it's the last scene of a block.

    :param session: Database session
    :param scene_id: Scene ID to check
    :param prop_id: Prop ID (if checking a prop)
    :param scenery_id: Scenery ID (if checking scenery)
    :param show: The show
    :returns: True if the scene is a valid STRIKE boundary
    """
    if prop_id is not None:
        prop = session.get(Props, prop_id)
        if not prop:
            return False
        blocks = compute_blocks_for_prop(prop, show)
    elif scenery_id is not None:
        scenery = session.get(Scenery, scenery_id)
        if not scenery:
            return False
        blocks = compute_blocks_for_scenery(scenery, show)
    else:
        return False

    return any(block.strike_scene_id == scene_id for block in blocks)


def is_valid_boundary(
    session: Session,
    scene_id: int,
    assignment_type: str,
    prop_id: int | None,
    scenery_id: int | None,
    show: Show,
) -> bool:
    """
    Check if a scene is a valid boundary for a crew assignment.

    :param session: Database session
    :param scene_id: Scene ID to check
    :param assignment_type: 'set' or 'strike'
    :param prop_id: Prop ID (if checking a prop)
    :param scenery_id: Scenery ID (if checking scenery)
    :param show: The show
    :returns: True if the scene is a valid boundary for the assignment type
    """
    if assignment_type == "set":
        return is_valid_set_boundary(session, scene_id, prop_id, scenery_id, show)
    elif assignment_type == "strike":
        return is_valid_strike_boundary(session, scene_id, prop_id, scenery_id, show)
    else:
        return False


def find_orphaned_assignments_for_prop(
    session: Session, prop: Props, show: Show
) -> List[CrewAssignment]:
    """
    Find crew assignments for a prop that are no longer on valid block boundaries.

    :param session: Database session
    :param prop: The prop to check
    :param show: The show
    :returns: List of orphaned CrewAssignment objects
    """
    blocks = compute_blocks_for_prop(prop, show)
    valid_set_scenes = {block.set_scene_id for block in blocks}
    valid_strike_scenes = {block.strike_scene_id for block in blocks}

    # Get all crew assignments for this prop
    assignments = session.scalars(
        select(CrewAssignment).where(CrewAssignment.prop_id == prop.id)
    ).all()

    orphaned = []
    for assignment in assignments:
        if assignment.assignment_type == "set":
            if assignment.scene_id not in valid_set_scenes:
                orphaned.append(assignment)
        elif assignment.assignment_type == "strike":
            if assignment.scene_id not in valid_strike_scenes:
                orphaned.append(assignment)

    return orphaned


def find_orphaned_assignments_for_scenery(
    session: Session, scenery: Scenery, show: Show
) -> List[CrewAssignment]:
    """
    Find crew assignments for a scenery item that are no longer on valid block boundaries.

    :param session: Database session
    :param scenery: The scenery item to check
    :param show: The show
    :returns: List of orphaned CrewAssignment objects
    """
    blocks = compute_blocks_for_scenery(scenery, show)
    valid_set_scenes = {block.set_scene_id for block in blocks}
    valid_strike_scenes = {block.strike_scene_id for block in blocks}

    # Get all crew assignments for this scenery
    assignments = session.scalars(
        select(CrewAssignment).where(CrewAssignment.scenery_id == scenery.id)
    ).all()

    orphaned = []
    for assignment in assignments:
        if assignment.assignment_type == "set":
            if assignment.scene_id not in valid_set_scenes:
                orphaned.append(assignment)
        elif assignment.assignment_type == "strike":
            if assignment.scene_id not in valid_strike_scenes:
                orphaned.append(assignment)

    return orphaned


def delete_orphaned_assignments_for_prop(
    session: Session, prop: Props, show: Show
) -> List[int]:
    """
    Delete crew assignments for a prop that are no longer on valid block boundaries.

    :param session: Database session
    :param prop: The prop to check
    :param show: The show
    :returns: List of IDs of deleted assignments
    """
    orphaned = find_orphaned_assignments_for_prop(session, prop, show)
    deleted_ids = [a.id for a in orphaned]

    for assignment in orphaned:
        session.delete(assignment)

    return deleted_ids


def delete_orphaned_assignments_for_scenery(
    session: Session, scenery: Scenery, show: Show
) -> List[int]:
    """
    Delete crew assignments for a scenery item that are no longer on valid block boundaries.

    :param session: Database session
    :param scenery: The scenery item to check
    :param show: The show
    :returns: List of IDs of deleted assignments
    """
    orphaned = find_orphaned_assignments_for_scenery(session, scenery, show)
    deleted_ids = [a.id for a in orphaned]

    for assignment in orphaned:
        session.delete(assignment)

    return deleted_ids
