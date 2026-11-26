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
