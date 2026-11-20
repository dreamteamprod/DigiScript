import { describe, it, expect, beforeEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useDraftPages } from './useDraftPages';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import type { SnapshotLine } from '@/js/yjs/yjsSnapshot';

function line(uid: string, id: number | null = null, text = uid): SnapshotLine {
  return {
    _id: id === null ? uid : String(id),
    _uid: uid,
    id,
    act_id: 1,
    scene_id: 1,
    line_type: 1,
    stage_direction_style_id: null,
    parts: [
      {
        _id: `${uid}-p`,
        _uid: `${uid}-p`,
        id: null,
        part_index: 0,
        character_id: 1,
        character_group_id: null,
        line_text: text,
      },
    ],
  };
}

function setPages(pages: Record<string, SnapshotLine[]>): void {
  useScriptDraftStore().pageSnapshots = pages;
}

describe('useDraftPages', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('defaults to a single page before anything has synced', () => {
    const { pageNumbers, maxPage } = useDraftPages();

    expect(pageNumbers.value).toEqual([]);
    expect(maxPage.value).toBe(1);
  });

  it('lists existing pages ascending and ignores non-page keys', () => {
    setPages({ '10': [], '2': [line('a')], '1': [], notes: [], '01': [], '0': [] });
    const { pageNumbers, maxPage } = useDraftPages();

    expect(pageNumbers.value).toEqual([1, 2, 10]);
    expect(maxPage.value).toBe(10);
  });

  it('follows the server adding a new trailing page', () => {
    setPages({ '1': [line('a')], '2': [] });
    const { maxPage } = useDraftPages();
    expect(maxPage.value).toBe(2);

    useScriptDraftStore().pageSnapshots['3'] = [];

    expect(maxPage.value).toBe(3);
  });

  it('presents a page in the ScriptLine shape, carrying _uid', () => {
    setPages({ '1': [line('a', 7, 'Hello')] });
    const { linesFor } = useDraftPages();

    const [first] = linesFor(1);

    expect(first).toMatchObject({ _uid: 'a', id: 7, page: 1, line_type: 1 });
    expect(first.line_parts[0].line_text).toBe('Hello');
    expect(linesFor(9)).toEqual([]);
  });

  describe('previousLineOf', () => {
    it('returns the line above on the same page', () => {
      setPages({ '1': [line('a'), line('b')] });
      const { previousLineOf } = useDraftPages();

      expect(previousLineOf(1, 1)?._uid).toBe('a');
    });

    it('is null at the very start of the script', () => {
      setPages({ '1': [line('a')] });
      const { previousLineOf } = useDraftPages();

      expect(previousLineOf(1, 0)).toBeNull();
    });

    it('crosses to the last line of the nearest earlier non-empty page', () => {
      setPages({ '1': [line('a'), line('b')], '2': [], '3': [line('c')] });
      const { previousLineOf } = useDraftPages();

      expect(previousLineOf(3, 0)?._uid).toBe('b');
    });
  });
});
