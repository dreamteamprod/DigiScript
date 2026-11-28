import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import type { ScriptLine } from '@/types/api/script';
import { computePageStatus, useScriptConfigStore } from './scriptConfig';
import { toast } from '@/js/toast';

vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

function makeLine(id: number | null, numParts: number): ScriptLine {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: 1,
    stage_direction_style_id: null,
    line_parts: Array.from({ length: numParts }, (_, i) => ({
      id: id == null ? null : 100 + i,
      line_id: id,
      part_index: i,
      character_id: 1,
      character_group_id: null,
      line_text: `Part ${i}`,
    })),
  };
}

describe('computePageStatus', () => {
  it('classifies an existing line whose line_parts grew as updated, not added', () => {
    const saved = [makeLine(42, 1)];
    const edited = [makeLine(42, 2)];

    const status = computePageStatus(saved, edited, [], []);

    expect(status.added).not.toContain(0);
    expect(status.updated).toContain(0);
    expect(status.deleted).toHaveLength(0);
    expect(status.inserted).toHaveLength(0);
  });

  it('classifies a genuinely new line (id == null) as added', () => {
    const saved: ScriptLine[] = [];
    const edited = [makeLine(null, 1)];

    const status = computePageStatus(saved, edited, [], []);

    expect(status.added).toContain(0);
    expect(status.updated).not.toContain(0);
  });

  it('classifies an existing line with a changed top-level field as updated', () => {
    const saved = [makeLine(42, 1)];
    const edited = [{ ...makeLine(42, 1), line_type: 2 }];

    const status = computePageStatus(saved, edited, [], []);

    expect(status.updated).toContain(0);
    expect(status.added).not.toContain(0);
  });

  it('passes deleted line indices through to the deleted array', () => {
    const saved = [makeLine(10, 1), makeLine(11, 1)];
    const edited = [makeLine(10, 1), makeLine(11, 1)];

    const status = computePageStatus(saved, edited, [1], []);

    expect(status.deleted).toContain(1);
    expect(status.added).toHaveLength(0);
    expect(status.updated).toHaveLength(0);
  });

  it('passes inserted line indices through to the inserted array', () => {
    const saved = [makeLine(10, 1)];
    const newLine = makeLine(null, 1);
    const edited = [makeLine(10, 1), newLine];

    const status = computePageStatus(saved, edited, [], [1]);

    expect(status.inserted).toContain(1);
  });

  it('handles a mixed page: one truly-new line and one existing line whose parts grew', () => {
    const saved = [makeLine(42, 1)];
    const edited = [makeLine(42, 2), makeLine(null, 1)];

    const status = computePageStatus(saved, edited, [], []);

    expect(status.updated).toContain(0);
    expect(status.added).not.toContain(0);
    expect(status.added).toContain(1);
    expect(status.updated).not.toContain(1);
  });

  it('returns all empty arrays when actual and tmp pages are identical', () => {
    const page = [makeLine(42, 2), makeLine(43, 1)];

    const status = computePageStatus(page, structuredClone(page), [], []);

    expect(status.added).toHaveLength(0);
    expect(status.updated).toHaveLength(0);
    expect(status.deleted).toHaveLength(0);
    expect(status.inserted).toHaveLength(0);
  });
});

describe('insertBlankLine after deleteLine shifts later indices', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('renumbers deletedLines when a new line is spliced in before it', () => {
    const store = useScriptConfigStore();
    const lines = [0, 1, 2, 3, 4, 5].map((n) => makeLine(100 + n, 1));
    store.addPage(1, lines);

    // Delete the saved line originally at index 5 — a tombstone, not spliced out.
    store.deleteLine(1, 5);
    expect(store.getDeletedLines(1)).toEqual([5]);
    expect(store.getTmpPage(1)[5]!.id).toBe(105);

    // Insert a new line at index 3 (e.g. pressing Enter on line index 2) — this
    // splices, shifting every later index (including the tombstone) up by one.
    store.insertBlankLine(1, 3, makeLine(null, 1));

    // The tombstone (line id 105) has physically moved to index 6, and
    // deletedLines must follow it there — otherwise, on save, index 5 (now a
    // different, live line) would be treated as deleted instead.
    expect(store.getTmpPage(1)[6]!.id).toBe(105);
    expect(store.getDeletedLines(1)).toEqual([6]);
  });

  it('renumbers insertedLines the same way', () => {
    const store = useScriptConfigStore();
    store.addPage(
      1,
      [0, 1, 2].map((n) => makeLine(100 + n, 1))
    );

    store.insertBlankLine(1, 2, makeLine(null, 1)); // new line at index 2
    expect(store.getInsertedLines(1)).toEqual([2]);

    store.insertBlankLine(1, 0, makeLine(null, 1)); // new line at index 0
    expect(store.getInsertedLines(1)).toEqual([3, 0]);
  });

  it('shifts later deletedLines/insertedLines down when a splice-out removes an earlier unsaved line', () => {
    const store = useScriptConfigStore();
    store.addPage(
      1,
      [0, 1, 2, 3].map((n) => makeLine(100 + n, 1))
    );

    store.deleteLine(1, 3); // tombstone at index 3
    store.insertBlankLine(1, 0, makeLine(null, 1)); // unsaved line at index 0, shifts tombstone to 4
    expect(store.getDeletedLines(1)).toEqual([4]);
    expect(store.getInsertedLines(1)).toEqual([0]);

    store.deleteLine(1, 0); // removes the unsaved line itself (splice-out)
    expect(store.getInsertedLines(1)).toEqual([]); // the deleted index itself, gone
    expect(store.getDeletedLines(1)).toEqual([3]); // shifted back down with it
  });
});

describe('requestEditFailure', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('shows the server reason when there is one', async () => {
    const store = useScriptConfigStore();
    vi.spyOn(store, 'getScriptConfigStatus').mockResolvedValue();

    await store.requestEditFailure({ reason: 'Collaborative editing is enabled' });

    expect(toast.error).toHaveBeenCalledWith(
      'Unable to edit script: Collaborative editing is enabled'
    );
  });

  it('falls back to a generic message with no reason', async () => {
    const store = useScriptConfigStore();
    vi.spyOn(store, 'getScriptConfigStatus').mockResolvedValue();

    await store.requestEditFailure();

    expect(toast.error).toHaveBeenCalledWith('Unable to edit script');
  });
});

describe('lineKeys stay aligned with tmpScript', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  const keys = (store: ReturnType<typeof useScriptConfigStore>, n: number): string[] =>
    Array.from({ length: n }, (_, i) => store.getLineKey(1, i));

  it('gives every loaded line a distinct key', () => {
    const store = useScriptConfigStore();
    store.addPage(1, [makeLine(1, 1), makeLine(2, 1), makeLine(3, 1)]);

    expect(new Set(keys(store, 3)).size).toBe(3);
  });

  it('an insert keeps every existing line’s key, shifting it with its line', () => {
    const store = useScriptConfigStore();
    store.addPage(1, [makeLine(1, 1), makeLine(2, 1)]);
    const [k0, k1] = keys(store, 2);

    store.insertBlankLine(1, 1, makeLine(null, 1)); // new line at index 1

    const after = keys(store, 3);
    expect(after[0]).toBe(k0);
    expect(after[2]).toBe(k1);
    expect([k0, k1]).not.toContain(after[1]);
  });

  it('splicing out an unsaved line removes just its key', () => {
    const store = useScriptConfigStore();
    store.addPage(1, [makeLine(1, 1), makeLine(2, 1)]);
    store.insertBlankLine(1, 1, makeLine(null, 1));
    const [k0, , k2] = keys(store, 3);

    store.deleteLine(1, 1);

    expect(keys(store, 2)).toEqual([k0, k2]);
  });

  it('tombstoning a saved line keeps every key in place', () => {
    const store = useScriptConfigStore();
    store.addPage(1, [makeLine(1, 1), makeLine(2, 1)]);
    const before = keys(store, 2);

    store.deleteLine(1, 0);

    expect(keys(store, 2)).toEqual(before);
  });

  it('reusing a tombstoned slot gives it a fresh key', () => {
    const store = useScriptConfigStore();
    store.addPage(1, [makeLine(1, 1), makeLine(2, 1)]);
    const [k0, k1] = keys(store, 2);
    store.deleteLine(1, 0);

    store.insertBlankLine(1, 0, makeLine(null, 1));

    const after = keys(store, 2);
    expect(after[0]).not.toBe(k0);
    expect(after[1]).toBe(k1);
  });

  it('editing a line in place (setLine) keeps its key', () => {
    const store = useScriptConfigStore();
    store.addPage(1, [makeLine(1, 1)]);
    const before = keys(store, 1);

    store.setLine(1, 0, makeLine(1, 2));

    expect(keys(store, 1)).toEqual(before);
  });

  it('appending a line adds a new key at the end', () => {
    const store = useScriptConfigStore();
    store.addPage(1, [makeLine(1, 1)]);
    const [k0] = keys(store, 1);

    store.addBlankLine(1, makeLine(null, 1));

    const after = keys(store, 2);
    expect(after[0]).toBe(k0);
    expect(after[1]).not.toBe(k0);
  });

  it('falls back to an index-derived key for a page populated without the actions', () => {
    const store = useScriptConfigStore();
    store.tmpScript['1'] = [makeLine(1, 1)];

    expect(store.getLineKey(1, 0)).toBe('page_1_line_0');
  });

  it('never starts a key array mid-page, which would misalign it with tmpScript', () => {
    const store = useScriptConfigStore();
    store.tmpScript['1'] = [makeLine(1, 1), makeLine(2, 1)];

    store.insertBlankLine(1, 1, makeLine(null, 1));

    expect(store.lineKeys['1']).toBeUndefined();
    expect(store.getLineKey(1, 1)).toBe('page_1_line_1');
  });

  it('does not leak keys for an emptied or removed page', () => {
    const store = useScriptConfigStore();
    store.addPage(1, [makeLine(1, 1)]);
    store.addPage(2, [makeLine(2, 1)]);

    store.removePage(2);
    expect(store.lineKeys['2']).toBeUndefined();
    store.emptyScript();
    expect(store.lineKeys).toEqual({});
  });
});
