import { describe, it, expect } from 'vitest';
import { computeBlocks, findOrphanedAssignments } from './blockOrphanUtils';

describe('blockOrphanUtils', () => {
  describe('computeBlocks', () => {
    it('returns empty array for empty inputs', () => {
      expect(computeBlocks([], new Set())).toEqual([]);
      expect(computeBlocks([], new Set([1]))).toEqual([]);
      expect(computeBlocks(null, null)).toEqual([]);
    });

    it('returns single block for one allocated scene', () => {
      const scenes = [{ id: 1, act: 1 }];
      const result = computeBlocks(scenes, new Set([1]));
      expect(result).toEqual([{ actId: 1, sceneIds: [1], setSceneId: 1, strikeSceneId: 1 }]);
    });

    it('returns one block for consecutive scenes in one act', () => {
      const scenes = [
        { id: 1, act: 1 },
        { id: 2, act: 1 },
        { id: 3, act: 1 },
      ];
      const result = computeBlocks(scenes, new Set([1, 2, 3]));
      expect(result).toEqual([{ actId: 1, sceneIds: [1, 2, 3], setSceneId: 1, strikeSceneId: 3 }]);
    });

    it('splits into two blocks when there is a gap in the middle', () => {
      const scenes = [
        { id: 1, act: 1 },
        { id: 2, act: 1 },
        { id: 3, act: 1 },
        { id: 4, act: 1 },
      ];
      const result = computeBlocks(scenes, new Set([1, 2, 4]));
      expect(result).toEqual([
        { actId: 1, sceneIds: [1, 2], setSceneId: 1, strikeSceneId: 2 },
        { actId: 1, sceneIds: [4], setSceneId: 4, strikeSceneId: 4 },
      ]);
    });

    it('breaks blocks at act boundaries even for consecutive scenes', () => {
      const scenes = [
        { id: 1, act: 1 },
        { id: 2, act: 1 },
        { id: 3, act: 2 },
        { id: 4, act: 2 },
      ];
      const result = computeBlocks(scenes, new Set([1, 2, 3, 4]));
      expect(result).toEqual([
        { actId: 1, sceneIds: [1, 2], setSceneId: 1, strikeSceneId: 2 },
        { actId: 2, sceneIds: [3, 4], setSceneId: 3, strikeSceneId: 4 },
      ]);
    });

    it('handles multiple acts with multiple blocks each', () => {
      const scenes = [
        { id: 1, act: 1 },
        { id: 2, act: 1 },
        { id: 3, act: 1 },
        { id: 4, act: 2 },
        { id: 5, act: 2 },
        { id: 6, act: 2 },
      ];
      // Allocated: 1, 3 (act 1 gap), 4, 6 (act 2 gap)
      const result = computeBlocks(scenes, new Set([1, 3, 4, 6]));
      expect(result).toEqual([
        { actId: 1, sceneIds: [1], setSceneId: 1, strikeSceneId: 1 },
        { actId: 1, sceneIds: [3], setSceneId: 3, strikeSceneId: 3 },
        { actId: 2, sceneIds: [4], setSceneId: 4, strikeSceneId: 4 },
        { actId: 2, sceneIds: [6], setSceneId: 6, strikeSceneId: 6 },
      ]);
    });

    it('ignores scenes not in the allocated set', () => {
      const scenes = [
        { id: 1, act: 1 },
        { id: 2, act: 1 },
        { id: 3, act: 1 },
      ];
      const result = computeBlocks(scenes, new Set([2]));
      expect(result).toEqual([{ actId: 1, sceneIds: [2], setSceneId: 2, strikeSceneId: 2 }]);
    });
  });

  describe('findOrphanedAssignments', () => {
    // Reusable test data
    const orderedScenes = [
      { id: 1, act: 1 },
      { id: 2, act: 1 },
      { id: 3, act: 1 },
      { id: 4, act: 1 },
    ];

    it('returns empty array when there are no crew assignments', () => {
      const result = findOrphanedAssignments({
        orderedScenes,
        currentAllocations: [{ scene_id: 1 }, { scene_id: 2 }],
        crewAssignments: [],
        changeType: 'remove',
        changeSceneId: 1,
      });
      expect(result).toEqual([]);
    });

    it('returns empty when boundary does not change', () => {
      // Block is scenes 1-3, remove scene 2 (middle) → boundaries stay at 1 and 3
      // Actually removing middle splits block: [1] and [3], boundaries change!
      // Use: remove scene 2 from [1,2,3] → [1] block (set=1,strike=1) + [3] (set=3,strike=3)
      // Original: [1,2,3] → set=1, strike=3
      // So boundaries DO change for strike. Let's use a case where they don't change.
      // Add scene 2 to [1,3] → no boundary change (set=1, strike=3 in both)
      const result = findOrphanedAssignments({
        orderedScenes,
        currentAllocations: [{ scene_id: 1 }, { scene_id: 3 }],
        crewAssignments: [
          { id: 10, scene_id: 1, assignment_type: 'set', crew_id: 1 },
          { id: 11, scene_id: 3, assignment_type: 'strike', crew_id: 2 },
        ],
        changeType: 'add',
        changeSceneId: 2,
      });
      expect(result).toEqual([]);
    });

    it('orphans SET assignments when block start is removed', () => {
      // Block [1,2,3] → remove scene 1 → block becomes [2,3], SET moves to 2
      const setAssignment = { id: 10, scene_id: 1, assignment_type: 'set', crew_id: 1 };
      const strikeAssignment = { id: 11, scene_id: 3, assignment_type: 'strike', crew_id: 2 };
      const result = findOrphanedAssignments({
        orderedScenes,
        currentAllocations: [{ scene_id: 1 }, { scene_id: 2 }, { scene_id: 3 }],
        crewAssignments: [setAssignment, strikeAssignment],
        changeType: 'remove',
        changeSceneId: 1,
      });
      expect(result).toEqual([setAssignment]);
    });

    it('orphans STRIKE assignments when block end is removed', () => {
      // Block [1,2,3] → remove scene 3 → block becomes [1,2], STRIKE moves to 2
      const setAssignment = { id: 10, scene_id: 1, assignment_type: 'set', crew_id: 1 };
      const strikeAssignment = { id: 11, scene_id: 3, assignment_type: 'strike', crew_id: 2 };
      const result = findOrphanedAssignments({
        orderedScenes,
        currentAllocations: [{ scene_id: 1 }, { scene_id: 2 }, { scene_id: 3 }],
        crewAssignments: [setAssignment, strikeAssignment],
        changeType: 'remove',
        changeSceneId: 3,
      });
      expect(result).toEqual([strikeAssignment]);
    });

    it('orphans both SET and STRIKE when a single-scene block is removed', () => {
      // Block [2] only → remove scene 2 → block disappears
      const setAssignment = { id: 10, scene_id: 2, assignment_type: 'set', crew_id: 1 };
      const strikeAssignment = { id: 11, scene_id: 2, assignment_type: 'strike', crew_id: 2 };
      const result = findOrphanedAssignments({
        orderedScenes,
        currentAllocations: [{ scene_id: 2 }],
        crewAssignments: [setAssignment, strikeAssignment],
        changeType: 'remove',
        changeSceneId: 2,
      });
      expect(result).toContainEqual(setAssignment);
      expect(result).toContainEqual(strikeAssignment);
      expect(result).toHaveLength(2);
    });

    it('does not orphan when removing a middle scene (split keeps original boundaries)', () => {
      // Block [1,2,3] → remove scene 2 → blocks [1] and [3]
      // SET scene 1 stays valid (set of block [1]), STRIKE scene 3 stays valid (strike of block [3])
      const result = findOrphanedAssignments({
        orderedScenes,
        currentAllocations: [{ scene_id: 1 }, { scene_id: 2 }, { scene_id: 3 }],
        crewAssignments: [
          { id: 10, scene_id: 1, assignment_type: 'set', crew_id: 1 },
          { id: 11, scene_id: 3, assignment_type: 'strike', crew_id: 2 },
        ],
        changeType: 'remove',
        changeSceneId: 2,
      });
      expect(result).toEqual([]);
    });

    it('orphans old SET when adding a scene before block start', () => {
      // Block [2,3] → add scene 1 → block becomes [1,2,3], SET moves to 1
      const oldSetAssignment = { id: 10, scene_id: 2, assignment_type: 'set', crew_id: 1 };
      const result = findOrphanedAssignments({
        orderedScenes,
        currentAllocations: [{ scene_id: 2 }, { scene_id: 3 }],
        crewAssignments: [
          oldSetAssignment,
          { id: 11, scene_id: 3, assignment_type: 'strike', crew_id: 2 },
        ],
        changeType: 'add',
        changeSceneId: 1,
      });
      expect(result).toEqual([oldSetAssignment]);
    });

    it('orphans old STRIKE when adding a scene after block end', () => {
      // Block [1,2] → add scene 3 → block becomes [1,2,3], STRIKE moves to 3
      const oldStrikeAssignment = { id: 11, scene_id: 2, assignment_type: 'strike', crew_id: 2 };
      const result = findOrphanedAssignments({
        orderedScenes,
        currentAllocations: [{ scene_id: 1 }, { scene_id: 2 }],
        crewAssignments: [
          { id: 10, scene_id: 1, assignment_type: 'set', crew_id: 1 },
          oldStrikeAssignment,
        ],
        changeType: 'add',
        changeSceneId: 3,
      });
      expect(result).toEqual([oldStrikeAssignment]);
    });

    it('does not affect assignments in a different act', () => {
      const multiActScenes = [
        { id: 1, act: 1 },
        { id: 2, act: 1 },
        { id: 3, act: 2 },
        { id: 4, act: 2 },
      ];
      // Act 1 block [1,2], Act 2 block [3,4]
      // Remove scene 1 (act 1 boundary change) → Act 2 should be unaffected
      const act1Set = { id: 10, scene_id: 1, assignment_type: 'set', crew_id: 1 };
      const act2Set = { id: 20, scene_id: 3, assignment_type: 'set', crew_id: 1 };
      const act2Strike = { id: 21, scene_id: 4, assignment_type: 'strike', crew_id: 2 };
      const result = findOrphanedAssignments({
        orderedScenes: multiActScenes,
        currentAllocations: [{ scene_id: 1 }, { scene_id: 2 }, { scene_id: 3 }, { scene_id: 4 }],
        crewAssignments: [act1Set, act2Set, act2Strike],
        changeType: 'remove',
        changeSceneId: 1,
      });
      // Only act1 SET is orphaned
      expect(result).toEqual([act1Set]);
    });
  });
});
