import type { ScriptLine } from '@/types/api/script';
import type { BulkEditPayload } from '@/types/bulkEdit';

/** Applies a `BulkEditPayload` to a single line, used by `ScriptEditor.vue`'s
 * `onBulkApply`. Pure, so it's unit-testable independently of the store/
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
