import type { ScriptLine } from '@/types/api/script';
import type { BulkEditPayload } from '@/types/bulkEdit';

/** `SetCharacterOrGroupDialog` only emits once one of the two is set (its own
 * `canApply` gate) — this narrows that into `BulkEditPayload['assignee']`'s
 * discriminated union shape (`null` if somehow neither is set), shared by both
 * `ScriptEditor.vue` and `CollabScriptEditor.vue`'s own `onSetCharacterApply`. */
export function narrowAssignee(assignee: {
  partIndex: number;
  characterId: number | null;
  characterGroupId: number | null;
}): BulkEditPayload['assignee'] {
  if (assignee.characterId != null) {
    return {
      partIndex: assignee.partIndex,
      characterId: assignee.characterId,
      characterGroupId: null,
    };
  }
  if (assignee.characterGroupId != null) {
    return {
      partIndex: assignee.partIndex,
      characterId: null,
      characterGroupId: assignee.characterGroupId,
    };
  }
  return null;
}

/** Applies a `BulkEditPayload` to a single line, used by `ScriptEditor.vue`'s
 * `applyToSelection`. Pure, so it's unit-testable independently of the store/
 * page-loading machinery around it. */
export function applyBulkPayloadToLine(line: ScriptLine, payload: BulkEditPayload): ScriptLine {
  let updatedLine = line;
  if (payload.actScene) {
    updatedLine = {
      ...updatedLine,
      act_id: payload.actScene.actId,
      scene_id: payload.actScene.sceneId,
    };
  }
  if (!payload.assignee) return updatedLine;

  const targetPartIdx = payload.assignee.partIndex - 1;
  const sortedParts = [...updatedLine.line_parts].sort(
    (a, b) => (a.part_index ?? 0) - (b.part_index ?? 0)
  );
  if (sortedParts.length <= targetPartIdx) return updatedLine;

  const { characterId, characterGroupId } = payload.assignee;
  return {
    ...updatedLine,
    line_parts: sortedParts.map((part, idx) =>
      idx === targetPartIdx
        ? { ...part, character_id: characterId, character_group_id: characterGroupId }
        : part
    ),
  };
}
