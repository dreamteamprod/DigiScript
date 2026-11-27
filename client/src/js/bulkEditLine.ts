import type { ScriptLine } from '@/types/api/script';
import type { BulkEditPayload } from '@/types/bulkEdit';

/** Applies a `BulkEditPayload` to a single line, used by `ScriptEditor.vue`'s
 * `applyToSelection`. Pure, so it's unit-testable independently of the store/
 * page-loading machinery around it. */
export function applyBulkPayloadToLine(line: ScriptLine, payload: BulkEditPayload): ScriptLine {
  if (payload.kind === 'actScene') {
    return { ...line, act_id: payload.actId, scene_id: payload.sceneId };
  }

  const targetPartIdx = payload.partIndex - 1;
  const sortedParts = [...line.line_parts].sort(
    (a, b) => (a.part_index ?? 0) - (b.part_index ?? 0)
  );
  if (sortedParts.length <= targetPartIdx) return line;

  const { characterId, characterGroupId } = payload;
  return {
    ...line,
    line_parts: sortedParts.map((part, idx) =>
      idx === targetPartIdx
        ? { ...part, character_id: characterId, character_group_id: characterGroupId }
        : part
    ),
  };
}
