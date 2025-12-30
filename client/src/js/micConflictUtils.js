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

export function areScenesInSameAct(sceneId1, sceneId2, sceneGraph) {
  const node1 = sceneGraph.find((n) => n.sceneId === sceneId1);
  const node2 = sceneGraph.find((n) => n.sceneId === sceneId2);

  if (!node1 || !node2) {
    return false;
  }

  return node1.actId === node2.actId;
}

export function isSameCastMember(characterId1, characterId2, characters, castList) {
  if (characterId1 === characterId2) {
    return true; // Same character, trivially same cast member
  }

  const char1 = characters.find((c) => c.id === characterId1);
  const char2 = characters.find((c) => c.id === characterId2);

  if (!char1 || !char2) {
    return false;
  }

  // Check cast_member.id (nested relationship) instead of played_by
  const castId1 = char1.cast_member?.id;
  const castId2 = char2.cast_member?.id;

  // Check if both have cast assignments (use == null to allow 0 as valid ID)
  if (castId1 == null || castId2 == null) {
    return false; // Conservative: no cast assignment = different cast members
  }

  return castId1 === castId2;
}

export function getConflictSeverity(sceneId1, sceneId2, sceneGraph) {
  const sameAct = areScenesInSameAct(sceneId1, sceneId2, sceneGraph);
  return sameAct ? 'WARNING' : 'INFO';
}

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

        // Build conflict message (shown on the destination scene being changed INTO)
        let message = `Quick-change from "${currentSceneNode?.sceneName || 'Unknown'}"`;
        if (char1 && char2) {
          message += ` (${char1.name} → ${char2.name})`;
        }
        if (severity === 'WARNING') {
          message += ' - Tight changeover required';
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
