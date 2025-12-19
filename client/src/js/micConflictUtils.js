/**
 * Microphone Conflict Detection Utilities
 *
 * This module provides pure functions for detecting microphone allocation conflicts
 * between adjacent scenes in a theatrical production.
 *
 * @module micConflictUtils
 */

/**
 * Builds a scene graph with adjacency information for conflict detection.
 * Traverses the linked list structure of acts and scenes to create a flat array
 * with position metadata and adjacency relationships.
 *
 * @param {Array} scenes - Array of scene objects
 * @param {Array} acts - Array of act objects
 * @param {Object} currentShow - Current show object with first_act_id
 * @returns {Array} Array of scene graph nodes with adjacency info
 */
export function buildSceneGraph(scenes, acts, currentShow) {
  if (!currentShow?.first_act_id || !scenes?.length || !acts?.length) {
    return [];
  }

  const sceneById = {};
  scenes.forEach((scene) => {
    sceneById[scene.id] = scene;
  });

  const actById = {};
  acts.forEach((act) => {
    actById[act.id] = act;
  });

  const graph = [];
  const graphById = {}; // Lookup object to avoid .find() in loops
  let globalPosition = 0;

  // Traverse acts in linked list order
  let currentAct = actById[currentShow.first_act_id];
  let previousActLastSceneId = null;

  while (currentAct != null) {
    let scenePosition = 0;
    let previousSceneId = null;

    // Traverse scenes within this act
    let currentScene = currentAct.first_scene ? sceneById[currentAct.first_scene] : null;

    while (currentScene != null) {
      const node = {
        sceneId: currentScene.id,
        actId: currentScene.act,
        sceneName: currentScene.name,
        actName: currentAct.name,
        globalPosition,
        scenePositionInAct: scenePosition,
        // Within-act adjacency
        previousSceneInAct: previousSceneId,
        nextSceneInAct: null, // Will be set when we process next scene
        // Cross-act adjacency
        previousSceneInShow: null,
        nextSceneInShow: null,
      };

      // Set next pointer for previous scene
      if (previousSceneId) {
        const prevNode = graphById[previousSceneId];
        if (prevNode) {
          prevNode.nextSceneInAct = currentScene.id;
          prevNode.nextSceneInShow = currentScene.id;
          node.previousSceneInShow = previousSceneId;
        }
      }

      // Handle cross-act boundary (last scene of previous act → first scene of this act)
      if (scenePosition === 0 && previousActLastSceneId) {
        const prevActLastNode = graphById[previousActLastSceneId];
        if (prevActLastNode) {
          prevActLastNode.nextSceneInShow = currentScene.id;
          node.previousSceneInShow = previousActLastSceneId;
        }
      }

      graph.push(node);
      graphById[currentScene.id] = node;

      previousSceneId = currentScene.id;
      currentScene = currentScene.next_scene ? sceneById[currentScene.next_scene] : null;
      scenePosition++;
      globalPosition++;
    }

    // Remember last scene of this act for cross-act linking
    previousActLastSceneId = previousSceneId;

    // Move to next act
    currentAct = currentAct.next_act ? actById[currentAct.next_act] : null;
  }

  return graph;
}

/**
 * Gets adjacent scenes for a given scene, distinguishing between same-act and cross-act adjacency.
 *
 * @param {number} sceneId - ID of the scene to find adjacency for
 * @param {Array} sceneGraph - Scene graph from buildSceneGraph()
 * @returns {Object} Object with adjacency info: { sameActPrev, sameActNext, crossActPrev, crossActNext }
 */
export function getAdjacentScenes(sceneId, sceneGraph) {
  const node = sceneGraph.find((n) => n.sceneId === sceneId);

  if (!node) {
    return {
      sameActPrev: null,
      sameActNext: null,
      crossActPrev: null,
      crossActNext: null,
    };
  }

  const prevNode = node.previousSceneInShow
    ? sceneGraph.find((n) => n.sceneId === node.previousSceneInShow)
    : null;
  const nextNode = node.nextSceneInShow
    ? sceneGraph.find((n) => n.sceneId === node.nextSceneInShow)
    : null;

  return {
    // Same act adjacency
    sameActPrev: prevNode && prevNode.actId === node.actId ? prevNode.sceneId : null,
    sameActNext: nextNode && nextNode.actId === node.actId ? nextNode.sceneId : null,
    // Cross-act adjacency (last scene of act N → first scene of act N+1)
    crossActPrev: prevNode && prevNode.actId !== node.actId ? prevNode.sceneId : null,
    crossActNext: nextNode && nextNode.actId !== node.actId ? nextNode.sceneId : null,
  };
}

/**
 * Checks if two scenes are in the same act.
 *
 * @param {number} sceneId1 - First scene ID
 * @param {number} sceneId2 - Second scene ID
 * @param {Array} sceneGraph - Scene graph from buildSceneGraph()
 * @returns {boolean} True if scenes are in the same act
 */
export function areScenesInSameAct(sceneId1, sceneId2, sceneGraph) {
  const node1 = sceneGraph.find((n) => n.sceneId === sceneId1);
  const node2 = sceneGraph.find((n) => n.sceneId === sceneId2);

  if (!node1 || !node2) {
    return false;
  }

  return node1.actId === node2.actId;
}

/**
 * Checks if two characters are played by the same cast member.
 * If either character has no cast assignment, returns false (conservative approach).
 *
 * @param {number} characterId1 - First character ID
 * @param {number} characterId2 - Second character ID
 * @param {Array} characters - Array of character objects
 * @param {Array} castList - Array of cast objects (optional, for future use)
 * @returns {boolean} True if same cast member plays both characters
 */
export function isSameCastMember(characterId1, characterId2, characters, castList) {
  if (characterId1 === characterId2) {
    return true; // Same character, trivially same cast member
  }

  const char1 = characters.find((c) => c.id === characterId1);
  const char2 = characters.find((c) => c.id === characterId2);

  if (!char1 || !char2) {
    return false;
  }

  // Check if both have cast assignments
  if (!char1.played_by || !char2.played_by) {
    return false; // Conservative: no cast assignment = different cast members
  }

  return char1.played_by === char2.played_by;
}

/**
 * Determines the severity of a conflict based on scene adjacency.
 *
 * @param {number} sceneId1 - First scene ID
 * @param {number} sceneId2 - Second scene ID (adjacent scene)
 * @param {Array} sceneGraph - Scene graph from buildSceneGraph()
 * @returns {string} 'WARNING' if same act, 'INFO' if cross-act
 */
export function getConflictSeverity(sceneId1, sceneId2, sceneGraph) {
  const sameAct = areScenesInSameAct(sceneId1, sceneId2, sceneGraph);
  return sameAct ? 'WARNING' : 'INFO';
}

/**
 * Detects all microphone conflicts in the allocation data.
 * A conflict occurs when the same microphone is allocated to different cast members
 * in adjacent scenes (within act or across act boundaries).
 *
 * @param {Object} allocations - Mic allocations object: { [micId]: { [sceneId]: characterId } }
 * @param {Array} scenes - Array of scene objects
 * @param {Array} acts - Array of act objects
 * @param {Object} currentShow - Current show object
 * @param {Array} characters - Array of character objects
 * @param {Array} castList - Array of cast objects (optional)
 * @returns {Object} Object with conflicts array and indexed lookups
 */
export function detectMicConflicts(allocations, scenes, acts, currentShow, characters, castList) {
  if (!allocations || !scenes?.length || !acts?.length || !currentShow) {
    return {
      conflicts: [],
      conflictsByScene: {},
      conflictsByMic: {},
    };
  }

  const sceneGraph = buildSceneGraph(scenes, acts, currentShow);

  if (sceneGraph.length === 0) {
    return {
      conflicts: [],
      conflictsByScene: {},
      conflictsByMic: {},
    };
  }

  const conflicts = [];

  // For each microphone
  Object.keys(allocations).forEach((micId) => {
    const micAllocations = allocations[micId];

    if (!micAllocations || typeof micAllocations !== 'object') {
      return;
    }

    // For each scene where this mic is allocated
    Object.keys(micAllocations).forEach((sceneId) => {
      const characterId = micAllocations[sceneId];

      if (characterId == null) {
        return; // No allocation in this scene
      }

      const sceneIdNum = parseInt(sceneId, 10);
      const adjacentScenes = getAdjacentScenes(sceneIdNum, sceneGraph);

      // Check all adjacent scenes (same act + cross act)
      const adjacentSceneIds = [
        adjacentScenes.sameActPrev,
        adjacentScenes.sameActNext,
        adjacentScenes.crossActPrev,
        adjacentScenes.crossActNext,
      ].filter((id) => id != null);

      adjacentSceneIds.forEach((adjacentSceneId) => {
        const adjacentCharacterId = micAllocations[adjacentSceneId];

        if (adjacentCharacterId == null) {
          return; // No allocation in adjacent scene
        }

        if (adjacentCharacterId === characterId) {
          return; // Same character keeps the mic (no conflict)
        }

        // Check if same cast member (no conflict if true)
        if (isSameCastMember(characterId, adjacentCharacterId, characters, castList)) {
          return; // Same actor keeps mic across characters
        }

        // We have a conflict! Determine severity
        const severity = getConflictSeverity(sceneIdNum, adjacentSceneId, sceneGraph);

        const currentSceneNode = sceneGraph.find((n) => n.sceneId === sceneIdNum);
        const adjacentSceneNode = sceneGraph.find((n) => n.sceneId === adjacentSceneId);

        const char1 = characters.find((c) => c.id === characterId);
        const char2 = characters.find((c) => c.id === adjacentCharacterId);

        // Build conflict message
        let message = `Same mic in adjacent scene "${adjacentSceneNode?.sceneName || 'Unknown'}"`;
        if (char1 && char2) {
          message += ` (${char1.name} → ${char2.name})`;
        }
        if (severity === 'WARNING') {
          message += ' - Tight quick-change required';
        } else {
          message += ' - Interval provides changeover time';
        }

        // Avoid duplicate conflicts (if scene A→B is a conflict, don't also add B→A)
        const isDuplicate = conflicts.some(
          (c) => c.micId === parseInt(micId, 10)
            && c.sceneId === adjacentSceneId
            && c.adjacentSceneId === sceneIdNum,
        );

        if (!isDuplicate) {
          conflicts.push({
            micId: parseInt(micId, 10),
            sceneId: sceneIdNum,
            sceneName: currentSceneNode?.sceneName || 'Unknown',
            actName: currentSceneNode?.actName || 'Unknown',
            characterId,
            characterName: char1?.name || 'Unknown',
            adjacentSceneId,
            adjacentSceneName: adjacentSceneNode?.sceneName || 'Unknown',
            adjacentActName: adjacentSceneNode?.actName || 'Unknown',
            adjacentCharacterId,
            adjacentCharacterName: char2?.name || 'Unknown',
            severity,
            message,
          });
        }
      });
    });
  });

  // Build indexed lookups
  const conflictsByScene = {};
  const conflictsByMic = {};

  conflicts.forEach((conflict) => {
    // Index by scene
    if (!conflictsByScene[conflict.sceneId]) {
      conflictsByScene[conflict.sceneId] = [];
    }
    conflictsByScene[conflict.sceneId].push(conflict);

    // Index by mic
    if (!conflictsByMic[conflict.micId]) {
      conflictsByMic[conflict.micId] = [];
    }
    conflictsByMic[conflict.micId].push(conflict);
  });

  return {
    conflicts,
    conflictsByScene,
    conflictsByMic,
  };
}
