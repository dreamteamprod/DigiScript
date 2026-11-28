import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import type { ScriptLine } from '@/types/api/script';
import type { Cue } from '@/types/api/cues';
import { toast } from '@/js/toast';
import { useScriptStore } from './script';

vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn(), warning: vi.fn() },
}));

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

describe('script store saveCuts', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.mocked(toast.error).mockClear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('resolves false and toasts when the request is rejected', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));

    await expect(useScriptStore().saveCuts([1])).resolves.toBe(false);
    expect(toast.error).toHaveBeenCalledWith('Unable to save script cuts');
  });

  it('resolves false and toasts on a non-OK response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false }));

    await expect(useScriptStore().saveCuts([1])).resolves.toBe(false);
    expect(toast.error).toHaveBeenCalledWith('Unable to save script cuts');
  });

  it('still resolves true, with a warning, when the PUT succeeds but the refresh fails', async () => {
    const store = useScriptStore();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
    vi.spyOn(store, 'getCuts').mockRejectedValue(new Error('refresh failed'));

    await expect(store.saveCuts([1])).resolves.toBe(true);
    expect(toast.warning).toHaveBeenCalledWith('Script cuts saved, but could not be refreshed');
    expect(toast.error).not.toHaveBeenCalled();
  });

  it('resolves true on success', async () => {
    const store = useScriptStore();
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
    vi.spyOn(store, 'getCuts').mockResolvedValue();

    await expect(store.saveCuts([1])).resolves.toBe(true);
  });
});

describe('script store cue loading and results', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubFetch(handler: (url: string, init?: RequestInit) => unknown) {
    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => handler(url, init));
    vi.stubGlobal('fetch', fetchMock);
    return fetchMock;
  }
  const ok = (body: unknown) => ({ ok: true, json: async () => body });
  const failed = { ok: false, json: async () => ({}) };

  it('loadCues keeps line_positions and reports success', async () => {
    stubFetch(() =>
      ok({
        cues: {},
        cue_groups: [],
        line_positions: { '5': { page: 2, index: 1, act_id: 1, scene_id: 1 } },
      })
    );
    const store = useScriptStore();

    expect(await store.loadCues()).toBe(true);
    expect(store.linePositions['5']).toEqual({ page: 2, index: 1, act_id: 1, scene_id: 1 });
  });

  it('loadCues copes with a server that sends no line_positions', async () => {
    stubFetch(() => ok({ cues: {}, cue_groups: [] }));
    const store = useScriptStore();
    store.linePositions = { '1': { page: 1, index: 0, act_id: 1, scene_id: 1 } };

    await store.loadCues();

    expect(store.linePositions).toEqual({});
  });

  it('loadCues reports failure and keeps what it had', async () => {
    stubFetch(() => failed);
    const store = useScriptStore();
    store.linePositions = { '1': { page: 1, index: 0, act_id: 1, scene_id: 1 } };

    expect(await store.loadCues()).toBe(false);
    expect(Object.keys(store.linePositions)).toEqual(['1']);
  });

  it.each([
    ['addNewCue', { cueType: 1, ident: '1', lineId: 1 }],
    ['editCue', { cueId: 1, cueType: 1, ident: '1', lineId: 1 }],
    ['deleteCue', { cueId: 1, lineId: 1 }],
    ['addCueGroup', { cueTypeId: 1, lineId: 1, cues: [{ ident: '1', sortOrder: 0 }] }],
    ['editCueGroup', { groupId: 1, lineId: 1, cues: [{ ident: '1', sortOrder: 0 }] }],
    ['deleteCueGroup', { groupId: 1, lineId: 1 }],
  ] as const)('%s reports success, and failure', async (action, payload) => {
    const store = useScriptStore();
    const call = (store as unknown as Record<string, (p: unknown) => Promise<boolean>>)[action];

    stubFetch((url) => (url.includes('/cues') && !url.includes('?') ? ok({}) : ok({ cues: {} })));
    expect(await call(payload)).toBe(true);

    stubFetch(() => failed);
    expect(await call(payload)).toBe(false);
  });

  it('reloads cue positions when a script page changes, once cues have been loaded', async () => {
    const fetchMock = stubFetch((url) =>
      url.includes('/show/script?')
        ? ok({ page: 1, lines: [] })
        : ok({ cues: {}, cue_groups: [], line_positions: {} })
    );
    const store = useScriptStore();

    await store.scriptPageChanged({ page: 1 });
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/show/cues'))).toBe(false);

    store.linePositions = { '1': { page: 1, index: 0, act_id: 1, scene_id: 1 } };
    await store.scriptPageChanged({ page: 1 });
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/show/cues'))).toBe(true);
  });
});
