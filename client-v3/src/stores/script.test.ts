import { describe, it, expect, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import type { ScriptLine } from '@/types/api/script';
import type { Cue } from '@/types/api/cues';
import { useScriptStore } from './script';

function makeLine(id: number): ScriptLine {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: 1,
    stage_direction_style_id: null,
    line_parts: [],
  };
}

function makeCue(id: number, cueTypeId: number, linePosition: number | null = 0): Cue {
  return {
    id,
    cue_type_id: cueTypeId,
    ident: String(id),
    group_id: null,
    sort_order: null,
    line_position: linePosition,
  };
}

describe('script store cue tracking getters', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('builds a line order index across pages', () => {
    const store = useScriptStore();
    store.script = {
      '1': [makeLine(10), makeLine(11)],
      '2': [makeLine(20)],
    };

    const index = store.lineOrderIndex;

    expect(index.get(10)).toEqual({ page: 1, index: 0 });
    expect(index.get(11)).toEqual({ page: 1, index: 1 });
    expect(index.get(20)).toEqual({ page: 2, index: 0 });
  });

  it('returns the last cue per cue type at or before the given position', () => {
    const store = useScriptStore();
    store.script = {
      '1': [makeLine(10), makeLine(11)],
      '2': [makeLine(20), makeLine(21)],
    };
    store.cues = {
      '10': [makeCue(1, 100), makeCue(2, 200)],
      '11': [makeCue(3, 100)],
      '20': [makeCue(4, 200)],
      '21': [makeCue(5, 100)],
    };

    // Position at page 1, line index 1 (line 11): cue type 100 -> cue 3, type 200 -> cue 2
    const atLine11 = store.lastCuePerTypeAt(1, 1);
    expect(atLine11[100].id).toBe(3);
    expect(atLine11[200].id).toBe(2);

    // Position at page 2, line index 0 (line 20): type 100 still cue 3 (last passed), type 200 -> cue 4
    const atLine20 = store.lastCuePerTypeAt(2, 0);
    expect(atLine20[100].id).toBe(3);
    expect(atLine20[200].id).toBe(4);

    // Position at page 2, line index 1 (line 21): type 100 -> cue 5 (overtakes cue 3)
    const atLine21 = store.lastCuePerTypeAt(2, 1);
    expect(atLine21[100].id).toBe(5);
    expect(atLine21[200].id).toBe(4);
  });

  it('ignores cues on lines not yet in the line order index', () => {
    const store = useScriptStore();
    store.script = { '1': [makeLine(10)] };
    store.cues = { '999': [makeCue(1, 100)] };

    const result = store.lastCuePerTypeAt(1, 0);

    expect(result).toEqual({});
  });

  it('breaks ties on the same line using line_position', () => {
    const store = useScriptStore();
    store.script = { '1': [makeLine(10)] };
    store.cues = {
      '10': [makeCue(1, 100, 0), makeCue(2, 100, 5)],
    };

    const result = store.lastCuePerTypeAt(1, 0);

    expect(result[100].id).toBe(2);
  });
});
