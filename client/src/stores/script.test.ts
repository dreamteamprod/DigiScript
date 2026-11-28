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
    vi.mocked(toast.success).mockClear();
    vi.mocked(toast.error).mockClear();
    vi.mocked(toast.warning).mockClear();
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
  const cuesBody = { cues: {}, cue_groups: [], line_positions: {} };
  const isCuesRead = (url: string, init?: RequestInit) =>
    /\/show\/cues$/.test(url) && (init?.method ?? 'GET') === 'GET';

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

  it('loadCues reports failure and keeps what it had, for a bad status and for a rejected request', async () => {
    const store = useScriptStore();
    store.linePositions = { '1': { page: 1, index: 0, act_id: 1, scene_id: 1 } };

    stubFetch(() => failed);
    expect(await store.loadCues()).toBe(false);

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(store.loadCues()).resolves.toBe(false);

    expect(Object.keys(store.linePositions)).toEqual(['1']);
    expect(store.cuesLoaded).toBe(false);
  });

  it('an empty result still counts as loaded', async () => {
    stubFetch(() => ok({ cues: {}, cue_groups: [], line_positions: {} }));
    const store = useScriptStore();
    expect(store.cuesLoaded).toBe(false);

    await store.loadCues();

    expect(store.cuesLoaded).toBe(true);
  });

  it('loadScriptPage resolves true when loaded, false (never rejects) when not', async () => {
    const store = useScriptStore();
    stubFetch(() => ok({ page: 3, lines: [{ id: 1 }] }));
    await expect(store.loadScriptPage(3)).resolves.toBe(true);
    expect(store.script['3']).toEqual([{ id: 1 }]);

    stubFetch(() => failed);
    await expect(store.loadScriptPage(4)).resolves.toBe(false);

    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(store.loadScriptPage(5)).resolves.toBe(false);
    expect(store.script['4']).toBeUndefined();
  });

  // [action, payload, method, URL matcher, expected body (null for a DELETE)]
  it.each([
    ['addNewCue', { cueType: 1, ident: '1', lineId: 2 }, 'POST', /\/show\/cues$/, true],
    ['editCue', { cueId: 3, cueType: 1, ident: '1', lineId: 2 }, 'PATCH', /\/show\/cues$/, true],
    ['deleteCue', { cueId: 3, lineId: 2 }, 'DELETE', /\/show\/cues\?cueId=3&lineId=2$/, false],
    [
      'addCueGroup',
      { cueTypeId: 1, lineId: 2, cues: [{ ident: '1', sortOrder: 0 }] },
      'POST',
      /\/show\/cues\/groups$/,
      true,
    ],
    [
      'editCueGroup',
      { groupId: 4, lineId: 2, cues: [{ ident: '1', sortOrder: 0 }] },
      'PATCH',
      /\/show\/cues\/groups$/,
      true,
    ],
    [
      'deleteCueGroup',
      { groupId: 4, lineId: 2 },
      'DELETE',
      /\/show\/cues\/groups\?groupId=4&lineId=2$/,
      false,
    ],
  ] as const)(
    '%s sends the right request, reloads, and reports success',
    async (action, payload, method, urlPattern, hasBody) => {
      const store = useScriptStore();
      const call = (store as unknown as Record<string, (p: unknown) => Promise<boolean>>)[action];
      const fetchMock = stubFetch((url, init) => (isCuesRead(url, init) ? ok(cuesBody) : ok({})));

      await expect(call(payload)).resolves.toBe(true);

      const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
      expect(url).toMatch(urlPattern);
      expect(init.method).toBe(method);
      if (hasBody) expect(JSON.parse(init.body as string)).toEqual(payload);
      // The cues are read again afterwards, and the person is told it worked.
      expect(fetchMock.mock.calls.some(([u, i]) => isCuesRead(String(u), i))).toBe(true);
      expect(toast.success).toHaveBeenCalledTimes(1);
      expect(toast.error).not.toHaveBeenCalled();
    }
  );

  it.each([
    ['addNewCue', { cueType: 1, ident: '1', lineId: 2 }],
    ['editCue', { cueId: 3, cueType: 1, ident: '1', lineId: 2 }],
    ['deleteCue', { cueId: 3, lineId: 2 }],
    ['addCueGroup', { cueTypeId: 1, lineId: 2, cues: [{ ident: '1', sortOrder: 0 }] }],
    ['editCueGroup', { groupId: 4, lineId: 2, cues: [{ ident: '1', sortOrder: 0 }] }],
    ['deleteCueGroup', { groupId: 4, lineId: 2 }],
  ] as const)(
    '%s reports failure, without reloading, when the server refuses or the request fails',
    async (action, payload) => {
      const store = useScriptStore();
      const call = (store as unknown as Record<string, (p: unknown) => Promise<boolean>>)[action];

      const fetchMock = stubFetch(() => failed);
      await expect(call(payload)).resolves.toBe(false);
      expect(fetchMock).toHaveBeenCalledTimes(1);

      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
      await expect(call(payload)).resolves.toBe(false);

      expect(toast.error).toHaveBeenCalledTimes(2);
      expect(toast.success).not.toHaveBeenCalled();
    }
  );

  it.each([
    ['addNewCue', { cueType: 1, ident: '1', lineId: 2 }],
    ['editCue', { cueId: 3, cueType: 1, ident: '1', lineId: 2 }],
    ['deleteCue', { cueId: 3, lineId: 2 }],
    ['addCueGroup', { cueTypeId: 1, lineId: 2, cues: [{ ident: '1', sortOrder: 0 }] }],
    ['editCueGroup', { groupId: 4, lineId: 2, cues: [{ ident: '1', sortOrder: 0 }] }],
    ['deleteCueGroup', { groupId: 4, lineId: 2 }],
  ] as const)(
    '%s still reports success, with a warning, when the change is saved but the refresh fails',
    async (action, payload) => {
      const store = useScriptStore();
      const call = (store as unknown as Record<string, (p: unknown) => Promise<boolean>>)[action];
      // The write goes through; reading the cues back does not. Reporting this as a failure
      // would let the person retry, and a retried add creates a duplicate.
      stubFetch((url, init) => (isCuesRead(url, init) ? failed : ok({})));

      await expect(call(payload)).resolves.toBe(true);

      expect(toast.warning).toHaveBeenCalledTimes(1);
      expect(vi.mocked(toast.warning).mock.calls[0][0]).toContain('could not be refreshed');
      expect(toast.error).not.toHaveBeenCalled();
      expect(toast.success).not.toHaveBeenCalled();
    }
  );

  it('still reports success when the refresh request itself rejects', async () => {
    const store = useScriptStore();
    stubFetch((url, init) => {
      if (isCuesRead(url, init)) throw new TypeError('Failed to fetch');
      return ok({});
    });

    await expect(store.addNewCue({ cueType: 1, ident: '1', lineId: 2 })).resolves.toBe(true);
    expect(toast.warning).toHaveBeenCalledTimes(1);
  });

  it('reloads cue positions when a script page changes, once cues have been loaded', async () => {
    const fetchMock = stubFetch((url) =>
      url.includes('/show/script?') ? ok({ page: 1, lines: [] }) : ok(cuesBody)
    );
    const store = useScriptStore();

    await store.scriptPageChanged({ page: 1 });
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/show/cues'))).toBe(false);

    // Loaded, even though no line has a cue: an empty result must not look like "not loaded".
    await store.loadCues();
    fetchMock.mockClear();
    await store.scriptPageChanged({ page: 1 });
    expect(fetchMock.mock.calls.some(([u]) => String(u).endsWith('/show/cues'))).toBe(true);
  });
});
