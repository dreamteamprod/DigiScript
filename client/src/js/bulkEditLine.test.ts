import { describe, it, expect } from 'vitest';
import { applyBulkPayloadToLine, narrowAssignee } from '@/js/bulkEditLine';
import type { ScriptLine } from '@/types/api/script';
import type { BulkEditPayload } from '@/types/bulkEdit';

function makeLine(overrides: Partial<ScriptLine> = {}): ScriptLine {
  return {
    id: 1,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: 0,
    stage_direction_style_id: null,
    line_parts: [
      {
        id: 1,
        line_id: 1,
        part_index: 0,
        character_id: null,
        character_group_id: null,
        line_text: 'Hi',
      },
    ],
    ...overrides,
  };
}

describe('applyBulkPayloadToLine', () => {
  it('applies act/scene, leaving line_parts untouched, when assignee is null', () => {
    const line = makeLine();
    const payload: BulkEditPayload = { actScene: { actId: 9, sceneId: 8 }, assignee: null };

    const result = applyBulkPayloadToLine(line, payload);

    expect(result.act_id).toBe(9);
    expect(result.scene_id).toBe(8);
    expect(result.line_parts).toBe(line.line_parts); // untouched, same reference
  });

  it('applies a character assignment to the target part, leaving act/scene untouched', () => {
    const line = makeLine();
    const payload: BulkEditPayload = {
      actScene: null,
      assignee: { partIndex: 1, characterId: 42, characterGroupId: null },
    };

    const result = applyBulkPayloadToLine(line, payload);

    expect(result.act_id).toBe(line.act_id);
    expect(result.line_parts[0]!.character_id).toBe(42);
    expect(result.line_parts[0]!.character_group_id).toBeNull();
  });

  it('applies a character-group assignment', () => {
    const line = makeLine();
    const payload: BulkEditPayload = {
      actScene: null,
      assignee: { partIndex: 1, characterId: null, characterGroupId: 7 },
    };

    const result = applyBulkPayloadToLine(line, payload);

    expect(result.line_parts[0]!.character_id).toBeNull();
    expect(result.line_parts[0]!.character_group_id).toBe(7);
  });

  it('applies both sections at once', () => {
    const line = makeLine();
    const payload: BulkEditPayload = {
      actScene: { actId: 2, sceneId: 3 },
      assignee: { partIndex: 1, characterId: 5, characterGroupId: null },
    };

    const result = applyBulkPayloadToLine(line, payload);

    expect(result.act_id).toBe(2);
    expect(result.scene_id).toBe(3);
    expect(result.line_parts[0]!.character_id).toBe(5);
  });

  it('leaves the line untouched when the target part index does not exist', () => {
    const line = makeLine(); // only 1 part, index 0
    const payload: BulkEditPayload = {
      actScene: null,
      assignee: { partIndex: 2, characterId: 5, characterGroupId: null }, // index 1 — out of range
    };

    const result = applyBulkPayloadToLine(line, payload);

    expect(result.line_parts).toEqual(line.line_parts);
  });

  it('sorts parts by part_index before locating the target, regardless of array order', () => {
    const line = makeLine({
      line_parts: [
        {
          id: 2,
          line_id: 1,
          part_index: 1,
          character_id: null,
          character_group_id: null,
          line_text: 'B',
        },
        {
          id: 1,
          line_id: 1,
          part_index: 0,
          character_id: null,
          character_group_id: null,
          line_text: 'A',
        },
      ],
    });
    const payload: BulkEditPayload = {
      actScene: null,
      assignee: { partIndex: 2, characterId: 9, characterGroupId: null }, // targets part_index 1
    };

    const result = applyBulkPayloadToLine(line, payload);

    const part = result.line_parts.find((p) => p.part_index === 1);
    expect(part?.character_id).toBe(9);
  });
});

describe('narrowAssignee', () => {
  it('narrows a character assignment, nulling the group field', () => {
    const result = narrowAssignee({ partIndex: 1, characterId: 42, characterGroupId: null });
    expect(result).toEqual({ partIndex: 1, characterId: 42, characterGroupId: null });
  });

  it('narrows a character-group assignment, nulling the character field', () => {
    const result = narrowAssignee({ partIndex: 1, characterId: null, characterGroupId: 7 });
    expect(result).toEqual({ partIndex: 1, characterId: null, characterGroupId: 7 });
  });

  it('prefers characterId when both are somehow set', () => {
    const result = narrowAssignee({ partIndex: 1, characterId: 42, characterGroupId: 7 });
    expect(result).toEqual({ partIndex: 1, characterId: 42, characterGroupId: null });
  });

  it('returns null when neither is set', () => {
    const result = narrowAssignee({ partIndex: 1, characterId: null, characterGroupId: null });
    expect(result).toBeNull();
  });
});
