import { describe, it, expect } from 'vitest';
import Vue from 'vue';
import Vuex from 'vuex';
import type { ScriptLine } from '@/types/api/script';
import type { Cue } from '@/types/api/cues';
import scriptModule from './script';

Vue.use(Vuex);

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

function makeStore() {
  return new Vuex.Store({
    modules: {
      script: { ...scriptModule, namespaced: true },
    },
  });
}

describe('script module cue tracking getters', () => {
  it('builds a line order index across pages', () => {
    const store = makeStore();
    store.replaceState({
      script: { script: { '1': [makeLine(10), makeLine(11)], '2': [makeLine(20)] } },
    } as any);

    const index = store.getters['script/LINE_ORDER_INDEX'];

    expect(index.get(10)).toEqual({ page: 1, index: 0 });
    expect(index.get(11)).toEqual({ page: 1, index: 1 });
    expect(index.get(20)).toEqual({ page: 2, index: 0 });
  });

  it('returns the last cue per cue type at or before the given position', () => {
    const store = makeStore();
    store.replaceState({
      script: {
        script: { '1': [makeLine(10), makeLine(11)], '2': [makeLine(20), makeLine(21)] },
        cues: {
          '10': [makeCue(1, 100), makeCue(2, 200)],
          '11': [makeCue(3, 100)],
          '20': [makeCue(4, 200)],
          '21': [makeCue(5, 100)],
        },
      },
    } as any);

    const atLine11 = store.getters['script/LAST_CUE_PER_TYPE_AT'](1, 1);
    expect(atLine11[100].id).toBe(3);
    expect(atLine11[200].id).toBe(2);

    const atLine20 = store.getters['script/LAST_CUE_PER_TYPE_AT'](2, 0);
    expect(atLine20[100].id).toBe(3);
    expect(atLine20[200].id).toBe(4);

    const atLine21 = store.getters['script/LAST_CUE_PER_TYPE_AT'](2, 1);
    expect(atLine21[100].id).toBe(5);
    expect(atLine21[200].id).toBe(4);
  });

  it('ignores cues on lines not yet in the line order index', () => {
    const store = makeStore();
    store.replaceState({
      script: {
        script: { '1': [makeLine(10)] },
        cues: { '999': [makeCue(1, 100)] },
      },
    } as any);

    expect(store.getters['script/LAST_CUE_PER_TYPE_AT'](1, 0)).toEqual({});
  });

  it('breaks ties on the same line using line_position', () => {
    const store = makeStore();
    store.replaceState({
      script: {
        script: { '1': [makeLine(10)] },
        cues: { '10': [makeCue(1, 100, 0), makeCue(2, 100, 5)] },
      },
    } as any);

    expect(store.getters['script/LAST_CUE_PER_TYPE_AT'](1, 0)[100].id).toBe(2);
  });
});
