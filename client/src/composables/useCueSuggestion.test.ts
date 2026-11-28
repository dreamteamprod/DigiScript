import { describe, it, expect } from 'vitest';
import {
  canonicalDecimal,
  nearestCues,
  orderedCuesOfType,
  splitAtLine,
  suggestCueNumber,
} from './useCueSuggestion';
import type { Cue, LinePosition } from '@/types/api/cues';

describe('canonicalDecimal', () => {
  it('strips leading and trailing zeros', () => {
    expect(canonicalDecimal('013.50')).toBe('13.5');
    expect(canonicalDecimal('14.0')).toBe('14');
    expect(canonicalDecimal('0.5')).toBe('0.5');
    expect(canonicalDecimal('0')).toBe('0');
  });
});

describe('suggestCueNumber', () => {
  // [before, after, also used, expected]
  const table: [string[], string[], string[], string | null][] = [
    [[], [], [], '1'],
    [['14'], [], [], '15'],
    [['14.5'], [], [], '15'],
    [['14'], [], ['15'], '16'],
    [[], ['5'], [], '4'],
    [[], ['4.5'], [], '4'],
    [[], ['1'], [], '0.5'],
    [['10'], ['14'], [], '11'],
    [['13'], ['14'], [], '13.5'],
    [['13', '13.5'], ['14'], [], '13.6'],
    [['13.9'], ['14'], [], '13.95'],
    [['13'], ['13.5'], [], '13.2'],
    [['13'], ['14'], ['13.5'], '13.4'],
    [['13', 'INTRO'], ['14'], [], '13.5'],
    [['13.01'], ['13.02'], [], null],
    [['20'], ['14'], [], null],
  ];

  it.each(table)('before=%j after=%j used=%j -> %s', (before, after, extraUsed, expected) => {
    const used = [...before, ...after, ...extraUsed];
    expect(suggestCueNumber(before, after, used).value).toBe(expected);
  });

  it('explains a blank when two neighbours leave no room', () => {
    const result = suggestCueNumber(['13.01'], ['13.02'], ['13.01', '13.02']);
    expect(result).toMatchObject({
      value: null,
      reason: 'no-free-number',
      previous: '13.01',
      next: '13.02',
    });
  });

  it('flags numbers that are out of order', () => {
    expect(suggestCueNumber(['20'], ['14'], ['20', '14']).reason).toBe('out-of-order');
  });

  it('ignores non-numeric idents when finding neighbours but counts numeric ones as used', () => {
    expect(suggestCueNumber(['INTRO'], [], ['INTRO']).value).toBe('1');
    expect(suggestCueNumber([], [], ['1', '2', 'X'])?.value).toBe('3');
  });

  it('treats equal decimals as the same number whatever their spelling', () => {
    // 13.50 is 13.5, so 13.5 is taken and 13.4 is the next nearest the midpoint.
    expect(suggestCueNumber(['13'], ['14'], ['13.50']).value).toBe('13.4');
  });

  it('uses exact decimal arithmetic, not floating point', () => {
    // 0.1 + 0.2 !== 0.3 in floats; here 13.1 -> 13.2 must be exact.
    expect(suggestCueNumber(['13', '13.1'], ['14'], []).value).toBe('13.2');
  });

  it('steps down past used whole numbers when only a following cue exists', () => {
    expect(suggestCueNumber([], ['5'], ['4', '3']).value).toBe('2');
  });

  it('is blank when every whole number below the following cue is used', () => {
    expect(suggestCueNumber([], ['3'], ['1', '2']).value).toBeNull();
  });

  it('is blank rather than needing a third decimal place for a half', () => {
    expect(suggestCueNumber([], ['0.01'], []).value).toBeNull();
    expect(suggestCueNumber([], ['0.5'], []).value).toBe('0.25');
  });
});

describe('positions from line_positions (pages that are not loaded)', () => {
  const cue = (id: number, ident: string, over: Partial<Cue> = {}): Cue => ({
    id,
    cue_type_id: 1,
    ident,
    group_id: null,
    sort_order: null,
    line_position: 1,
    ...over,
  });
  const pos = (page: number, index: number): LinePosition => ({
    page,
    index,
    act_id: 1,
    scene_id: 1,
  });

  // Neighbours live on pages 2 and 9; the person is on page 5, which holds no cues.
  const cuesByLine = {
    '10': [cue(1, '13')],
    '20': [cue(2, '14')],
    '30': [cue(3, 'SND-ONE', { cue_type_id: 2 })],
  };
  const linePositions = { '10': pos(2, 4), '20': pos(9, 0), '30': pos(5, 1) };

  it('orders cues of one type by page, line index, then position on the line', () => {
    const more = {
      ...cuesByLine,
      '11': [cue(4, 'b', { line_position: 2 }), cue(5, 'a', { line_position: 1 })],
    };
    const ordered = orderedCuesOfType(more, { ...linePositions, '11': pos(2, 4) }, 1);
    expect(ordered.map((e) => e.cue.ident)).toEqual(['13', 'a', 'b', '14']);
  });

  it('suggests from neighbours that are only on unloaded pages', () => {
    const ordered = orderedCuesOfType(cuesByLine, linePositions, 1);
    const { before, after } = splitAtLine(ordered, { page: 5, index: 3 });
    const used = ordered.map((e) => e.cue.ident);
    const result = suggestCueNumber(
      before.map((e) => e.cue.ident),
      after.map((e) => e.cue.ident),
      used
    );
    expect(result.value).toBe('13.5');
  });

  it('leaves out cues whose line position is unknown, but still counts them as used', () => {
    const withUnknown = { ...cuesByLine, '99': [cue(6, '15')] };
    const ordered = orderedCuesOfType(withUnknown, linePositions, 1);
    expect(ordered.map((e) => e.cue.ident)).toEqual(['13', '14']);
    // An unknown position must not become "before everything": 15 stays only in `used`.
    const used = Object.values(withUnknown)
      .flat()
      .filter((c) => c.cue_type_id === 1)
      .map((c) => c.ident);
    expect(suggestCueNumber(['14'], [], used).value).toBe('16');
  });

  it('puts cues on the current line before the new one (on or above)', () => {
    const ordered = orderedCuesOfType(cuesByLine, linePositions, 1);
    const { before, after } = splitAtLine(ordered, { page: 9, index: 0 });
    expect(before.map((e) => e.cue.ident)).toEqual(['13', '14']);
    expect(after).toEqual([]);
  });

  it('labels nearest cues above, this line, below, or by page', () => {
    const ordered = orderedCuesOfType(
      {
        a: [cue(1, '1')],
        b: [cue(2, '2')],
        c: [cue(3, '3')],
      },
      { a: pos(5, 0), b: pos(5, 2), c: pos(7, 0) },
      1
    );
    expect(nearestCues(ordered, { page: 5, index: 1 })).toMatchObject({
      previous: { where: 'above' },
      next: { where: 'below' },
    });
    expect(nearestCues(ordered, { page: 5, index: 2 })).toMatchObject({
      previous: { where: 'this line' },
      next: { where: 'page 7' },
    });
    expect(nearestCues(ordered, { page: 6, index: 0 })).toMatchObject({
      previous: { where: 'page 5' },
      next: { where: 'page 7' },
    });
    expect(nearestCues(ordered, { page: 1, index: 0 }).previous).toBeNull();
    expect(nearestCues(ordered, { page: 8, index: 0 }).next).toBeNull();
  });
});
