import { describe, it, expect } from 'vitest';
import * as Y from 'yjs';
import {
  zeroToNull,
  nullToZero,
  parseDbId,
  ydocLineToPlain,
  ydocPageToPlain,
  ydocPagesToPlain,
  ydocDeletedLineIds,
} from './yjsSnapshot';

interface LineOverrides {
  _id: string;
  act_id?: number;
  scene_id?: number;
  line_type?: number;
  stage_direction_style_id?: number;
  parts?: {
    _id: string;
    part_index?: number;
    character_id?: number;
    character_group_id?: number;
    text?: string;
  }[];
}

// A Y.Map/Y.Array can only ever be integrated into one place — pushing an
// already-integrated one into a second array corrupts the doc. So this builds an
// un-integrated Y.Map and lets the caller push it into wherever it belongs exactly once.
function makeLineMap(overrides: LineOverrides): Y.Map<unknown> {
  const lineMap = new Y.Map<unknown>();
  lineMap.set('_id', overrides._id);
  lineMap.set('act_id', overrides.act_id ?? 0);
  lineMap.set('scene_id', overrides.scene_id ?? 0);
  lineMap.set('line_type', overrides.line_type ?? 1);
  lineMap.set('stage_direction_style_id', overrides.stage_direction_style_id ?? 0);

  const partsArr = new Y.Array<Y.Map<unknown>>();
  lineMap.set('parts', partsArr);
  (overrides.parts ?? []).forEach((p) => {
    const partMap = new Y.Map<unknown>();
    partMap.set('_id', p._id);
    partMap.set('part_index', p.part_index ?? 0);
    partMap.set('character_id', p.character_id ?? 0);
    partMap.set('character_group_id', p.character_group_id ?? 0);
    partMap.set('line_text', new Y.Text(p.text ?? ''));
    partsArr.push([partMap]);
  });

  return lineMap;
}

describe('zeroToNull / nullToZero', () => {
  it('round-trips through the 0-sentinel used by the Y.Doc', () => {
    expect(zeroToNull(0)).toBeNull();
    expect(zeroToNull(5)).toBe(5);
    expect(nullToZero(null)).toBe(0);
    expect(nullToZero(undefined)).toBe(0);
    expect(nullToZero(5)).toBe(5);
  });
});

describe('parseDbId', () => {
  it('parses a positive integer string as a real DB id', () => {
    expect(parseDbId('123')).toBe(123);
  });

  it('treats 0 and negative values as not-a-DB-row', () => {
    expect(parseDbId('0')).toBeNull();
    expect(parseDbId('-1')).toBeNull();
  });

  it('treats a UUID string as a new, unsaved line', () => {
    expect(parseDbId('3fa85f64-5717-4562-b3fc-2c963f66afa6')).toBeNull();
  });

  it('does not misread a leading digit as a numeric prefix of a non-numeric string', () => {
    expect(parseDbId('9abc')).toBeNull();
  });
});

describe('ydocLineToPlain', () => {
  it('converts a Y.Map line into a plain snapshot, including nested Y.Text', () => {
    const doc = new Y.Doc();
    const pages = doc.getMap('pages');
    const pageArr = new Y.Array<Y.Map<unknown>>();
    pages.set('1', pageArr);
    const lineMap = makeLineMap({
      _id: '42',
      act_id: 1,
      scene_id: 2,
      line_type: 3,
      stage_direction_style_id: 0,
      parts: [{ _id: '99', part_index: 0, character_id: 5, character_group_id: 0, text: 'Hello' }],
    });
    pageArr.push([lineMap]);

    const snapshot = ydocLineToPlain(lineMap);

    expect(snapshot).toEqual({
      _id: '42',
      id: 42,
      act_id: 1,
      scene_id: 2,
      line_type: 3,
      stage_direction_style_id: null,
      parts: [
        {
          _id: '99',
          id: 99,
          part_index: 0,
          character_id: 5,
          character_group_id: null,
          line_text: 'Hello',
        },
      ],
    });
  });

  it('gives a new (UUID _id) line a null numeric id', () => {
    const doc = new Y.Doc();
    const holder = doc.getArray<Y.Map<unknown>>('holder');
    const lineMap = makeLineMap({ _id: 'abc-uuid', parts: [] });
    holder.push([lineMap]);

    const snapshot = ydocLineToPlain(lineMap);
    expect(snapshot.id).toBeNull();
    expect(snapshot._id).toBe('abc-uuid');
  });
});

describe('ydocPageToPlain / ydocPagesToPlain', () => {
  it('snapshots every page keyed by the same page-number strings the Y.Doc uses', () => {
    const doc = new Y.Doc();
    const pages = doc.getMap('pages');

    const page1 = new Y.Array<Y.Map<unknown>>();
    pages.set('1', page1);
    page1.push([makeLineMap({ _id: '1' }), makeLineMap({ _id: '2' })]);

    const page2 = new Y.Array<Y.Map<unknown>>();
    pages.set('2', page2);
    page2.push([makeLineMap({ _id: '3' })]);

    const snapshot = ydocPagesToPlain(doc);

    expect(Object.keys(snapshot).sort()).toEqual(['1', '2']);
    expect(snapshot['1']).toHaveLength(2);
    expect(snapshot['2']).toHaveLength(1);
    expect(ydocPageToPlain(page1)).toHaveLength(2);
  });

  it('returns an empty object for a doc with no pages yet', () => {
    const doc = new Y.Doc();
    expect(ydocPagesToPlain(doc)).toEqual({});
  });
});

describe('ydocDeletedLineIds', () => {
  it('parses only real DB ids out of deleted_line_ids, dropping UUID/0 entries', () => {
    const doc = new Y.Doc();
    const arr = doc.getArray<string>('deleted_line_ids');
    arr.push(['10', '0', 'some-uuid', '20']);

    expect(ydocDeletedLineIds(doc)).toEqual([10, 20]);
  });
});
