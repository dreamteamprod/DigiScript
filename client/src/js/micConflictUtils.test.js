import { describe, it, expect } from 'vitest';
import {
  buildSceneGraph,
  getAdjacentScenes,
  areScenesInSameAct,
  isSameCastMember,
  getConflictSeverity,
  detectMicConflicts,
} from './micConflictUtils';

describe('micConflictUtils', () => {
  describe('buildSceneGraph', () => {
    it('should return empty array when currentShow is null', () => {
      const scenes = [{ id: 1, name: 'Scene 1' }];
      const acts = [{ id: 1, name: 'Act 1' }];
      const result = buildSceneGraph(scenes, acts, null);
      expect(result).toEqual([]);
    });

    it('should return empty array when scenes array is empty', () => {
      const scenes = [];
      const acts = [{ id: 1, name: 'Act 1' }];
      const currentShow = { first_act_id: 1 };
      const result = buildSceneGraph(scenes, acts, currentShow);
      expect(result).toEqual([]);
    });

    it('should return empty array when acts array is empty', () => {
      const scenes = [{ id: 1, name: 'Scene 1' }];
      const acts = [];
      const currentShow = { first_act_id: 1 };
      const result = buildSceneGraph(scenes, acts, currentShow);
      expect(result).toEqual([]);
    });

    it('should build graph for single act with single scene', () => {
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };

      const result = buildSceneGraph(scenes, acts, currentShow);

      expect(result).toHaveLength(1);
      expect(result[0]).toMatchObject({
        sceneId: 1,
        actId: 1,
        sceneName: 'Scene 1',
        actName: 'Act 1',
        globalPosition: 0,
        scenePositionInAct: 0,
        previousSceneInAct: null,
        nextSceneInAct: null,
        previousSceneInShow: null,
        nextSceneInShow: null,
      });
    });

    it('should link multiple scenes within same act', () => {
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Scene 2', next_scene: 3,
        },
        {
          id: 3, act: 1, name: 'Scene 3', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };

      const result = buildSceneGraph(scenes, acts, currentShow);

      expect(result).toHaveLength(3);

      // Scene 1
      expect(result[0]).toMatchObject({
        sceneId: 1,
        previousSceneInAct: null,
        nextSceneInAct: 2,
        previousSceneInShow: null,
        nextSceneInShow: 2,
      });

      // Scene 2
      expect(result[1]).toMatchObject({
        sceneId: 2,
        previousSceneInAct: 1,
        nextSceneInAct: 3,
        previousSceneInShow: 1,
        nextSceneInShow: 3,
      });

      // Scene 3
      expect(result[2]).toMatchObject({
        sceneId: 3,
        previousSceneInAct: 2,
        nextSceneInAct: null,
        previousSceneInShow: 2,
        nextSceneInShow: null,
      });
    });

    it('should link scenes across act boundaries', () => {
      const scenes = [
        {
          id: 1, act: 1, name: 'Act 1 Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Act 1 Scene 2', next_scene: null,
        },
        {
          id: 3, act: 2, name: 'Act 2 Scene 1', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: 2,
        },
        {
          id: 2, name: 'Act 2', first_scene: 3, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };

      const result = buildSceneGraph(scenes, acts, currentShow);

      expect(result).toHaveLength(3);

      // Last scene of Act 1 (Scene 2)
      expect(result[1]).toMatchObject({
        sceneId: 2,
        actId: 1,
        nextSceneInAct: null, // No next scene in Act 1
        nextSceneInShow: 3, // But links to first scene of Act 2
      });

      // First scene of Act 2 (Scene 3)
      expect(result[2]).toMatchObject({
        sceneId: 3,
        actId: 2,
        previousSceneInAct: null, // No previous scene in Act 2
        previousSceneInShow: 2, // But links to last scene of Act 1
      });
    });

    it('should set correct global positions', () => {
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Scene 2', next_scene: null,
        },
        {
          id: 3, act: 2, name: 'Scene 3', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: 2,
        },
        {
          id: 2, name: 'Act 2', first_scene: 3, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };

      const result = buildSceneGraph(scenes, acts, currentShow);

      expect(result[0].globalPosition).toBe(0);
      expect(result[1].globalPosition).toBe(1);
      expect(result[2].globalPosition).toBe(2);
    });
  });

  describe('getAdjacentScenes', () => {
    it('should return all nulls for non-existent scene', () => {
      const sceneGraph = [];
      const result = getAdjacentScenes(999, sceneGraph);

      expect(result).toEqual({
        sameActPrev: null,
        sameActNext: null,
        crossActPrev: null,
        crossActNext: null,
      });
    });

    it('should return same-act adjacency for middle scene', () => {
      const sceneGraph = [
        {
          sceneId: 1,
          actId: 1,
          previousSceneInShow: null,
          nextSceneInShow: 2,
        },
        {
          sceneId: 2,
          actId: 1,
          previousSceneInShow: 1,
          nextSceneInShow: 3,
        },
        {
          sceneId: 3,
          actId: 1,
          previousSceneInShow: 2,
          nextSceneInShow: null,
        },
      ];

      const result = getAdjacentScenes(2, sceneGraph);

      expect(result).toEqual({
        sameActPrev: 1,
        sameActNext: 3,
        crossActPrev: null,
        crossActNext: null,
      });
    });

    it('should return cross-act adjacency for last scene of act', () => {
      const sceneGraph = [
        {
          sceneId: 1,
          actId: 1,
          previousSceneInShow: null,
          nextSceneInShow: 2,
        },
        {
          sceneId: 2,
          actId: 2,
          previousSceneInShow: 1,
          nextSceneInShow: null,
        },
      ];

      const result = getAdjacentScenes(1, sceneGraph);

      expect(result).toEqual({
        sameActPrev: null,
        sameActNext: null,
        crossActPrev: null,
        crossActNext: 2, // Cross-act to scene in Act 2
      });
    });

    it('should return cross-act adjacency for first scene of act', () => {
      const sceneGraph = [
        {
          sceneId: 1,
          actId: 1,
          previousSceneInShow: null,
          nextSceneInShow: 2,
        },
        {
          sceneId: 2,
          actId: 2,
          previousSceneInShow: 1,
          nextSceneInShow: null,
        },
      ];

      const result = getAdjacentScenes(2, sceneGraph);

      expect(result).toEqual({
        sameActPrev: null,
        sameActNext: null,
        crossActPrev: 1, // Cross-act from scene in Act 1
        crossActNext: null,
      });
    });
  });

  describe('areScenesInSameAct', () => {
    it('should return false when first scene not found', () => {
      const sceneGraph = [
        { sceneId: 1, actId: 1 },
        { sceneId: 2, actId: 2 },
      ];

      const result = areScenesInSameAct(999, 2, sceneGraph);
      expect(result).toBe(false);
    });

    it('should return false when second scene not found', () => {
      const sceneGraph = [
        { sceneId: 1, actId: 1 },
        { sceneId: 2, actId: 2 },
      ];

      const result = areScenesInSameAct(1, 999, sceneGraph);
      expect(result).toBe(false);
    });

    it('should return true when scenes are in same act', () => {
      const sceneGraph = [
        { sceneId: 1, actId: 1 },
        { sceneId: 2, actId: 1 },
      ];

      const result = areScenesInSameAct(1, 2, sceneGraph);
      expect(result).toBe(true);
    });

    it('should return false when scenes are in different acts', () => {
      const sceneGraph = [
        { sceneId: 1, actId: 1 },
        { sceneId: 2, actId: 2 },
      ];

      const result = areScenesInSameAct(1, 2, sceneGraph);
      expect(result).toBe(false);
    });
  });

  describe('isSameCastMember', () => {
    it('should return true for same character ID', () => {
      const characters = [
        { id: 1, name: 'Hamlet', played_by: 10 },
      ];
      const result = isSameCastMember(1, 1, characters, []);
      expect(result).toBe(true);
    });

    it('should return false when first character not found', () => {
      const characters = [
        { id: 1, name: 'Hamlet', played_by: 10 },
      ];
      const result = isSameCastMember(999, 1, characters, []);
      expect(result).toBe(false);
    });

    it('should return false when second character not found', () => {
      const characters = [
        { id: 1, name: 'Hamlet', played_by: 10 },
      ];
      const result = isSameCastMember(1, 999, characters, []);
      expect(result).toBe(false);
    });

    it('should return false when first character has no cast assignment', () => {
      const characters = [
        { id: 1, name: 'Hamlet', played_by: null },
        { id: 2, name: 'Ophelia', played_by: 20 },
      ];
      const result = isSameCastMember(1, 2, characters, []);
      expect(result).toBe(false);
    });

    it('should return false when second character has no cast assignment', () => {
      const characters = [
        { id: 1, name: 'Hamlet', played_by: 10 },
        { id: 2, name: 'Ophelia', played_by: null },
      ];
      const result = isSameCastMember(1, 2, characters, []);
      expect(result).toBe(false);
    });

    it('should return true when same cast member plays both characters', () => {
      const characters = [
        { id: 1, name: 'Hamlet', played_by: 10 },
        { id: 2, name: 'Ghost', played_by: 10 }, // Same actor
      ];
      const result = isSameCastMember(1, 2, characters, []);
      expect(result).toBe(true);
    });

    it('should return false when different cast members', () => {
      const characters = [
        { id: 1, name: 'Hamlet', played_by: 10 },
        { id: 2, name: 'Ophelia', played_by: 20 },
      ];
      const result = isSameCastMember(1, 2, characters, []);
      expect(result).toBe(false);
    });
  });

  describe('getConflictSeverity', () => {
    it('should return WARNING for scenes in same act', () => {
      const sceneGraph = [
        { sceneId: 1, actId: 1 },
        { sceneId: 2, actId: 1 },
      ];
      const result = getConflictSeverity(1, 2, sceneGraph);
      expect(result).toBe('WARNING');
    });

    it('should return INFO for scenes in different acts', () => {
      const sceneGraph = [
        { sceneId: 1, actId: 1 },
        { sceneId: 2, actId: 2 },
      ];
      const result = getConflictSeverity(1, 2, sceneGraph);
      expect(result).toBe('INFO');
    });
  });

  describe('detectMicConflicts', () => {
    it('should return empty conflicts when allocations is null', () => {
      const result = detectMicConflicts(null, [], [], {}, [], []);
      expect(result).toEqual({
        conflicts: [],
        conflictsByScene: {},
        conflictsByMic: {},
      });
    });

    it('should return empty conflicts when no scenes', () => {
      const allocations = { 1: { 1: 10 } };
      const result = detectMicConflicts(allocations, [], [], {}, [], []);
      expect(result).toEqual({
        conflicts: [],
        conflictsByScene: {},
        conflictsByMic: {},
      });
    });

    it('should not detect conflict when same character in adjacent scenes', () => {
      const allocations = {
        1: { // Mic 1
          1: 10, // Scene 1 -> Character 10
          2: 10, // Scene 2 -> Same character
        },
      };
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Scene 2', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };
      const characters = [
        { id: 10, name: 'Hamlet', played_by: 100 },
      ];

      const result = detectMicConflicts(allocations, scenes, acts, currentShow, characters, []);

      expect(result.conflicts).toHaveLength(0);
    });

    it('should not detect conflict when same cast member plays different characters', () => {
      const allocations = {
        1: { // Mic 1
          1: 10, // Scene 1 -> Hamlet
          2: 11, // Scene 2 -> Ghost (same actor)
        },
      };
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Scene 2', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };
      const characters = [
        { id: 10, name: 'Hamlet', played_by: 100 },
        { id: 11, name: 'Ghost', played_by: 100 }, // Same actor
      ];

      const result = detectMicConflicts(allocations, scenes, acts, currentShow, characters, []);

      expect(result.conflicts).toHaveLength(0);
    });

    it('should detect conflict when different cast members in same act', () => {
      const allocations = {
        1: { // Mic 1
          1: 10, // Scene 1 -> Hamlet
          2: 11, // Scene 2 -> Ophelia (different actor)
        },
      };
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Scene 2', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };
      const characters = [
        { id: 10, name: 'Hamlet', played_by: 100 },
        { id: 11, name: 'Ophelia', played_by: 200 }, // Different actor
      ];

      const result = detectMicConflicts(allocations, scenes, acts, currentShow, characters, []);

      expect(result.conflicts).toHaveLength(1);
      expect(result.conflicts[0]).toMatchObject({
        micId: 1,
        sceneId: 1,
        sceneName: 'Scene 1',
        characterId: 10,
        characterName: 'Hamlet',
        adjacentSceneId: 2,
        adjacentSceneName: 'Scene 2',
        adjacentCharacterId: 11,
        adjacentCharacterName: 'Ophelia',
        severity: 'WARNING', // Same act
      });
      expect(result.conflicts[0].message).toContain('Tight quick-change required');
    });

    it('should detect conflict when different cast members across acts', () => {
      const allocations = {
        1: { // Mic 1
          1: 10, // Last scene of Act 1 -> Hamlet
          2: 11, // First scene of Act 2 -> Ophelia (different actor)
        },
      };
      const scenes = [
        {
          id: 1, act: 1, name: 'Act 1 Scene 1', next_scene: null,
        },
        {
          id: 2, act: 2, name: 'Act 2 Scene 1', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: 2,
        },
        {
          id: 2, name: 'Act 2', first_scene: 2, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };
      const characters = [
        { id: 10, name: 'Hamlet', played_by: 100 },
        { id: 11, name: 'Ophelia', played_by: 200 }, // Different actor
      ];

      const result = detectMicConflicts(allocations, scenes, acts, currentShow, characters, []);

      expect(result.conflicts).toHaveLength(1);
      expect(result.conflicts[0]).toMatchObject({
        micId: 1,
        severity: 'INFO', // Cross-act
      });
      expect(result.conflicts[0].message).toContain('Interval provides changeover time');
    });

    it('should avoid duplicate conflicts', () => {
      const allocations = {
        1: { // Mic 1
          1: 10, // Scene 1 -> Hamlet
          2: 11, // Scene 2 -> Ophelia
          3: 10, // Scene 3 -> Hamlet again
        },
      };
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Scene 2', next_scene: 3,
        },
        {
          id: 3, act: 1, name: 'Scene 3', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };
      const characters = [
        { id: 10, name: 'Hamlet', played_by: 100 },
        { id: 11, name: 'Ophelia', played_by: 200 },
      ];

      const result = detectMicConflicts(allocations, scenes, acts, currentShow, characters, []);

      // Should have 2 conflicts: 1→2 and 2→3, but not 2→1 (duplicate of 1→2)
      expect(result.conflicts).toHaveLength(2);
    });

    it('should index conflicts by scene', () => {
      const allocations = {
        1: { 1: 10, 2: 11 },
      };
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Scene 2', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };
      const characters = [
        { id: 10, name: 'Hamlet', played_by: 100 },
        { id: 11, name: 'Ophelia', played_by: 200 },
      ];

      const result = detectMicConflicts(allocations, scenes, acts, currentShow, characters, []);

      expect(result.conflictsByScene[1]).toHaveLength(1);
      expect(result.conflictsByScene[1][0].sceneId).toBe(1);
    });

    it('should index conflicts by mic', () => {
      const allocations = {
        1: { 1: 10, 2: 11 },
      };
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Scene 2', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };
      const characters = [
        { id: 10, name: 'Hamlet', played_by: 100 },
        { id: 11, name: 'Ophelia', played_by: 200 },
      ];

      const result = detectMicConflicts(allocations, scenes, acts, currentShow, characters, []);

      expect(result.conflictsByMic[1]).toHaveLength(1);
      expect(result.conflictsByMic[1][0].micId).toBe(1);
    });

    it('should handle characters with no cast assignment conservatively', () => {
      const allocations = {
        1: { 1: 10, 2: 11 },
      };
      const scenes = [
        {
          id: 1, act: 1, name: 'Scene 1', next_scene: 2,
        },
        {
          id: 2, act: 1, name: 'Scene 2', next_scene: null,
        },
      ];
      const acts = [
        {
          id: 1, name: 'Act 1', first_scene: 1, next_act: null,
        },
      ];
      const currentShow = { first_act_id: 1 };
      const characters = [
        { id: 10, name: 'Hamlet', played_by: null }, // No cast
        { id: 11, name: 'Ophelia', played_by: 200 },
      ];

      const result = detectMicConflicts(allocations, scenes, acts, currentShow, characters, []);

      // Should detect conflict because no cast assignment = conservative approach
      expect(result.conflicts).toHaveLength(1);
    });
  });
});
