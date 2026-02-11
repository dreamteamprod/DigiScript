/**
 * Block computation and orphan detection utilities for stage crew assignments.
 *
 * A "block" is a consecutive sequence of scenes (within an act) where an item
 * is allocated. The first scene is the SET boundary; the last is the STRIKE
 * boundary. These pure functions mirror the backend logic in
 * server/utils/show/block_computation.py.
 */

/**
 * Compute allocation blocks from ordered scenes and a set of allocated scene IDs.
 *
 * Blocks break at act boundaries and allocation gaps.
 *
 * @param {Array<{id: number, act: number}>} orderedScenes - Scenes in display order
 * @param {Set<number>} allocatedSceneIds - Scene IDs where the item is allocated
 * @returns {Array<{actId: number, sceneIds: number[], setSceneId: number, strikeSceneId: number}>}
 */
export function computeBlocks(orderedScenes, allocatedSceneIds) {
  if (
    !orderedScenes ||
    orderedScenes.length === 0 ||
    !allocatedSceneIds ||
    allocatedSceneIds.size === 0
  ) {
    return [];
  }

  const blocks = [];
  let currentBlockScenes = [];
  let currentActId = null;

  for (const scene of orderedScenes) {
    // Act boundary breaks the current block
    if (currentActId !== null && scene.act !== currentActId) {
      if (currentBlockScenes.length > 0) {
        blocks.push({
          actId: currentActId,
          sceneIds: [...currentBlockScenes],
          setSceneId: currentBlockScenes[0],
          strikeSceneId: currentBlockScenes[currentBlockScenes.length - 1],
        });
        currentBlockScenes = [];
      }
    }
    currentActId = scene.act;

    if (allocatedSceneIds.has(scene.id)) {
      currentBlockScenes.push(scene.id);
    } else if (currentBlockScenes.length > 0) {
      blocks.push({
        actId: currentActId,
        sceneIds: [...currentBlockScenes],
        setSceneId: currentBlockScenes[0],
        strikeSceneId: currentBlockScenes[currentBlockScenes.length - 1],
      });
      currentBlockScenes = [];
    }
  }

  // Flush last block
  if (currentBlockScenes.length > 0) {
    blocks.push({
      actId: currentActId,
      sceneIds: [...currentBlockScenes],
      setSceneId: currentBlockScenes[0],
      strikeSceneId: currentBlockScenes[currentBlockScenes.length - 1],
    });
  }

  return blocks;
}

/**
 * Find crew assignments that would become orphaned by adding or removing
 * a scene allocation.
 *
 * @param {Object} params
 * @param {Array<{id: number, act: number}>} params.orderedScenes - All scenes in order
 * @param {Array<{scene_id: number}>} params.currentAllocations - Current allocations for the item
 * @param {Array<{id: number, scene_id: number, assignment_type: string, crew_id: number}>} params.crewAssignments - Current crew assignments for the item
 * @param {'add'|'remove'} params.changeType - Whether a scene allocation is being added or removed
 * @param {number} params.changeSceneId - The scene ID being added/removed
 * @returns {Array<{id: number, scene_id: number, assignment_type: string, crew_id: number}>} Orphaned assignments
 */
export function findOrphanedAssignments({
  orderedScenes,
  currentAllocations,
  crewAssignments,
  changeType,
  changeSceneId,
}) {
  if (!crewAssignments || crewAssignments.length === 0) {
    return [];
  }

  // Build current allocated set
  const currentSet = new Set(currentAllocations.map((a) => a.scene_id));

  // Simulate the change
  const newSet = new Set(currentSet);
  if (changeType === 'add') {
    newSet.add(changeSceneId);
  } else if (changeType === 'remove') {
    newSet.delete(changeSceneId);
  }

  // Compute blocks before and after
  const oldBlocks = computeBlocks(orderedScenes, currentSet);
  const newBlocks = computeBlocks(orderedScenes, newSet);

  // Build valid boundary sets from new blocks
  const validSetScenes = new Set(newBlocks.map((b) => b.setSceneId));
  const validStrikeScenes = new Set(newBlocks.map((b) => b.strikeSceneId));

  // Also check which assignments were valid before — only flag ones that
  // become invalid (were on a valid boundary before, but aren't after)
  const oldValidSetScenes = new Set(oldBlocks.map((b) => b.setSceneId));
  const oldValidStrikeScenes = new Set(oldBlocks.map((b) => b.strikeSceneId));

  return crewAssignments.filter((assignment) => {
    if (assignment.assignment_type === 'set') {
      const wasValid = oldValidSetScenes.has(assignment.scene_id);
      const isValid = validSetScenes.has(assignment.scene_id);
      return wasValid && !isValid;
    } else if (assignment.assignment_type === 'strike') {
      const wasValid = oldValidStrikeScenes.has(assignment.scene_id);
      const isValid = validStrikeScenes.has(assignment.scene_id);
      return wasValid && !isValid;
    }
    return false;
  });
}
