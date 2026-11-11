import type { Act, Character, Scene, Show } from '@/types/api/show';

export interface SceneGraphNode {
  sceneId: number;
  actId: number;
  sceneName: string;
  actName: string;
  globalPosition: number;
  scenePositionInAct: number;
  previousSceneInAct: number | null;
  nextSceneInAct: number | null;
  previousSceneInShow: number | null;
  nextSceneInShow: number | null;
}

export interface AdjacentScenes {
  sameActPrev: number | null;
  sameActNext: number | null;
  crossActPrev: number | null;
  crossActNext: number | null;
}

export interface MicConflict {
  micId: number;
  sceneId: number;
  sceneName: string;
  actName: string;
  characterId: number;
  characterName: string;
  adjacentSceneId: number;
  adjacentSceneName: string;
  adjacentActName: string;
  adjacentCharacterId: number;
  adjacentCharacterName: string;
  severity: 'WARNING' | 'INFO';
  message: string;
}

export interface MicConflictResult {
  conflicts: MicConflict[];
  conflictsByScene: Record<number, MicConflict[]>;
  conflictsByMic: Record<number, MicConflict[]>;
}

// Nested dict: { micId: { sceneId: characterId | null } }
type MicAllocations = Record<string, Record<string, number | null> | null>;

function linkSceneNode(
  nodeSceneId: number,
  graphById: Record<number, SceneGraphNode>,
  previousSceneId: number | null,
  scenePosition: number,
  previousActLastSceneId: number | null
): number | null {
  let previousSceneInShow: number | null = null;
  if (previousSceneId) {
    const prevNode = graphById[previousSceneId];
    if (prevNode) {
      prevNode.nextSceneInAct = nodeSceneId;
      prevNode.nextSceneInShow = nodeSceneId;
      previousSceneInShow = previousSceneId;
    }
  }
  if (scenePosition === 0 && previousActLastSceneId) {
    const prevActLastNode = graphById[previousActLastSceneId];
    if (prevActLastNode) {
      prevActLastNode.nextSceneInShow = nodeSceneId;
      previousSceneInShow = previousActLastSceneId;
    }
  }
  return previousSceneInShow;
}

export function buildSceneGraph(
  scenes: Scene[],
  acts: Act[],
  currentShow: Pick<Show, 'first_act_id'> | null
): SceneGraphNode[] {
  if (!currentShow?.first_act_id || !scenes?.length || !acts?.length) {
    return [];
  }

  const sceneById: Record<number, Scene> = Object.fromEntries(scenes.map((s) => [s.id, s]));
  const actById: Record<number, Act> = Object.fromEntries(acts.map((a) => [a.id, a]));

  const graph: SceneGraphNode[] = [];
  const graphById: Record<number, SceneGraphNode> = {};
  let globalPosition = 0;

  let currentAct: Act | null = actById[currentShow.first_act_id];
  let previousActLastSceneId: number | null = null;

  while (currentAct != null) {
    let scenePosition = 0;
    let previousSceneId: number | null = null;
    let currentScene = currentAct.first_scene ? sceneById[currentAct.first_scene] : null;

    while (currentScene != null) {
      const node: SceneGraphNode = {
        sceneId: currentScene.id,
        actId: currentScene.act!,
        sceneName: currentScene.name!,
        actName: currentAct.name!,
        globalPosition,
        scenePositionInAct: scenePosition,
        previousSceneInAct: previousSceneId,
        nextSceneInAct: null,
        previousSceneInShow: null,
        nextSceneInShow: null,
      };

      node.previousSceneInShow = linkSceneNode(
        node.sceneId,
        graphById,
        previousSceneId,
        scenePosition,
        previousActLastSceneId
      );

      graph.push(node);
      graphById[currentScene.id] = node;

      previousSceneId = currentScene.id;
      currentScene = currentScene.next_scene ? sceneById[currentScene.next_scene] : null;
      scenePosition++;
      globalPosition++;
    }

    previousActLastSceneId = previousSceneId;
    currentAct = currentAct.next_act ? actById[currentAct.next_act] : null;
  }

  return graph;
}

export function getAdjacentScenes(sceneId: number, sceneGraph: SceneGraphNode[]): AdjacentScenes {
  const node = sceneGraph.find((n) => n.sceneId === sceneId);

  if (!node) {
    return { sameActPrev: null, sameActNext: null, crossActPrev: null, crossActNext: null };
  }

  const prevNode = node.previousSceneInShow
    ? sceneGraph.find((n) => n.sceneId === node.previousSceneInShow)
    : null;
  const nextNode = node.nextSceneInShow
    ? sceneGraph.find((n) => n.sceneId === node.nextSceneInShow)
    : null;

  return {
    sameActPrev: prevNode?.actId === node.actId ? prevNode.sceneId : null,
    sameActNext: nextNode?.actId === node.actId ? nextNode.sceneId : null,
    crossActPrev: prevNode && prevNode.actId !== node.actId ? prevNode.sceneId : null,
    crossActNext: nextNode && nextNode.actId !== node.actId ? nextNode.sceneId : null,
  };
}

export function areScenesInSameAct(
  sceneId1: number,
  sceneId2: number,
  sceneGraph: SceneGraphNode[]
): boolean {
  const node1 = sceneGraph.find((n) => n.sceneId === sceneId1);
  const node2 = sceneGraph.find((n) => n.sceneId === sceneId2);
  if (!node1 || !node2) return false;
  return node1.actId === node2.actId;
}

export function isSameCastMember(
  characterId1: number,
  characterId2: number,
  characters: Character[],
  castList: unknown[]
): boolean {
  if (characterId1 === characterId2) return true;

  const char1 = characters.find((c) => c.id === characterId1);
  const char2 = characters.find((c) => c.id === characterId2);
  if (!char1 || !char2) return false;

  const castId1 = char1.cast_member?.id;
  const castId2 = char2.cast_member?.id;
  if (castId1 == null || castId2 == null) return false;

  return castId1 === castId2;
}

export function getConflictSeverity(
  sceneId1: number,
  sceneId2: number,
  sceneGraph: SceneGraphNode[]
): 'WARNING' | 'INFO' {
  return areScenesInSameAct(sceneId1, sceneId2, sceneGraph) ? 'WARNING' : 'INFO';
}

function buildConflictRecord(
  micId: number,
  sceneIdNum: number,
  adjacentSceneId: number,
  characterId: number,
  adjacentCharacterId: number,
  sceneGraph: SceneGraphNode[],
  characters: Character[]
): MicConflict {
  const severity = getConflictSeverity(sceneIdNum, adjacentSceneId, sceneGraph);
  const currentSceneNode = sceneGraph.find((n) => n.sceneId === sceneIdNum);
  const adjacentSceneNode = sceneGraph.find((n) => n.sceneId === adjacentSceneId);
  const char1 = characters.find((c) => c.id === characterId);
  const char2 = characters.find((c) => c.id === adjacentCharacterId);

  let message = `Quick-change from "${currentSceneNode?.sceneName || 'Unknown'}"`;
  if (char1 && char2) message += ` (${char1.name} → ${char2.name})`;
  message +=
    severity === 'WARNING'
      ? ' - Tight changeover required'
      : ' - Interval provides changeover time';

  return {
    micId,
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
  };
}

function checkAdjacentScene(
  conflicts: MicConflict[],
  micId: number,
  sceneIdNum: number,
  adjacentSceneId: number,
  characterId: number,
  micAllocations: Record<string, number | null>,
  sceneGraph: SceneGraphNode[],
  characters: Character[],
  castList: unknown[]
): void {
  const adjacentCharacterId = micAllocations[adjacentSceneId];
  if (adjacentCharacterId == null || adjacentCharacterId === characterId) return;
  if (isSameCastMember(characterId, adjacentCharacterId, characters, castList)) return;

  const isDuplicate = conflicts.some(
    (c) => c.micId === micId && c.sceneId === adjacentSceneId && c.adjacentSceneId === sceneIdNum
  );
  if (!isDuplicate) {
    conflicts.push(
      buildConflictRecord(
        micId,
        sceneIdNum,
        adjacentSceneId,
        characterId,
        adjacentCharacterId,
        sceneGraph,
        characters
      )
    );
  }
}

export function detectMicConflicts(
  allocations: MicAllocations,
  scenes: Scene[],
  acts: Act[],
  currentShow: Pick<Show, 'first_act_id'> | null,
  characters: Character[],
  castList: unknown[]
): MicConflictResult {
  if (!allocations || !scenes?.length || !acts?.length || !currentShow) {
    return { conflicts: [], conflictsByScene: {}, conflictsByMic: {} };
  }

  const sceneGraph = buildSceneGraph(scenes, acts, currentShow);
  if (sceneGraph.length === 0) {
    return { conflicts: [], conflictsByScene: {}, conflictsByMic: {} };
  }

  const conflicts: MicConflict[] = [];

  Object.keys(allocations).forEach((micId) => {
    const micAllocations = allocations[micId];
    if (!micAllocations || typeof micAllocations !== 'object') return;
    const micIdNum = Number.parseInt(micId, 10);

    Object.keys(micAllocations).forEach((sceneId) => {
      const characterId = micAllocations[sceneId];
      if (characterId == null) return;

      const sceneIdNum = Number.parseInt(sceneId, 10);
      const adjacentScenes = getAdjacentScenes(sceneIdNum, sceneGraph);
      const adjacentSceneIds = [
        adjacentScenes.sameActPrev,
        adjacentScenes.sameActNext,
        adjacentScenes.crossActPrev,
        adjacentScenes.crossActNext,
      ].filter((id): id is number => id != null);

      adjacentSceneIds.forEach((adjacentSceneId) => {
        checkAdjacentScene(
          conflicts,
          micIdNum,
          sceneIdNum,
          adjacentSceneId,
          characterId,
          micAllocations,
          sceneGraph,
          characters,
          castList
        );
      });
    });
  });

  const conflictsByScene: Record<number, MicConflict[]> = {};
  const conflictsByMic: Record<number, MicConflict[]> = {};

  conflicts.forEach((conflict) => {
    if (!conflictsByScene[conflict.sceneId]) conflictsByScene[conflict.sceneId] = [];
    conflictsByScene[conflict.sceneId].push(conflict);
    if (!conflictsByMic[conflict.micId]) conflictsByMic[conflict.micId] = [];
    conflictsByMic[conflict.micId].push(conflict);
  });

  return { conflicts, conflictsByScene, conflictsByMic };
}
