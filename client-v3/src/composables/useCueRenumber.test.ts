import { describe, expect, it } from 'vitest';
import {
  NUMERIC_IDENT_REGEX,
  NUMERIC_PREFIX_REGEX,
  computeRenumber,
  useCueRenumber,
} from './useCueRenumber';
import type { CueWithLineId } from './useCueRenumber';
import type { Cue } from '@/types/api/cues';

function makeCue(id: number, ident: string | null, cueTypeId = 1): CueWithLineId {
  return {
    id,
    ident,
    cue_type_id: cueTypeId,
    group_id: null,
    sort_order: null,
    line_position: null,
    line_id: 100,
  };
}

describe('NUMERIC_IDENT_REGEX', () => {
  it.each(['1', '42', '2.1', '100.01', '0', '9.99'])('matches numeric ident "%s"', (ident) => {
    expect(NUMERIC_IDENT_REGEX.test(ident)).toBe(true);
  });

  it.each(['', 'LX-1', '2.1x', '1.', ' 1', 'Q1 GO', '1a', 'INTRO', '1.111', '.5'])(
    'rejects non-numeric ident "%s"',
    (ident) => {
      expect(NUMERIC_IDENT_REGEX.test(ident)).toBe(false);
    }
  );
});

describe('NUMERIC_PREFIX_REGEX', () => {
  it.each([
    ['1', '1', ''],
    ['2.1', '2.1', ''],
    ['1 - House', '1', ' - House'],
    ['2.1 - Blackout', '2.1', ' - Blackout'],
    ['202 - LASER', '202', ' - LASER'],
  ])('extracts prefix and suffix from "%s"', (ident, prefix, suffix) => {
    const match = NUMERIC_PREFIX_REGEX.exec(ident);
    expect(match).not.toBeNull();
    expect(match![1]).toBe(prefix);
    expect(match![2]).toBe(suffix);
  });

  it.each(['', 'LX-INTRO', 'Q1 GO', '.5', 'INTRO'])('does not match "%s"', (ident) => {
    expect(NUMERIC_PREFIX_REGEX.exec(ident)).toBeNull();
  });
});

describe('computeRenumber', () => {
  it('assigns sequential integers sorted by parseFloat', () => {
    const cues = ['2.1', '1', '3', '2', '2.2'].map((ident, i) => makeCue(i, ident));
    const { allMatched, changes } = computeRenumber(cues);

    expect(allMatched.map((m) => m.computedIdent)).toEqual(['1', '2', '3', '4', '5']);
    // "1"→"1" and "2"→"2" stay the same; "2.1"→"3", "2.2"→"4", "3"→"5" change
    expect(changes).toHaveLength(3);
  });

  it('returns empty changes when cues are already sequential', () => {
    const cues = ['1', '2', '3'].map((ident, i) => makeCue(i, ident));
    const { allMatched, changes } = computeRenumber(cues);

    expect(changes).toHaveLength(0);
    expect(allMatched).toHaveLength(3);
    expect(allMatched.map((m) => m.computedIdent)).toEqual(['1', '2', '3']);
  });

  it('allMatched contains ALL matched cues including unchanged ones', () => {
    const cues = ['1', '2', '3'].map((ident, i) => makeCue(i, ident));
    const { allMatched } = computeRenumber(cues);
    expect(allMatched).toHaveLength(3);
  });

  it('separates non-numeric idents into unmatched', () => {
    const cues = [makeCue(1, '1'), makeCue(2, 'LX-INTRO'), makeCue(3, '2'), makeCue(4, '')];
    const { allMatched, changes, unmatched } = computeRenumber(cues);

    expect(allMatched).toHaveLength(2);
    expect(changes).toHaveLength(0); // 1→1, 2→2 — no changes
    expect(unmatched).toHaveLength(2);
    expect(unmatched.every((u) => !u.include)).toBe(true);
    expect(unmatched.every((u) => u.newIdent === '')).toBe(true);
  });

  it('treats null ident as unmatched', () => {
    const cues = [makeCue(1, null), makeCue(2, '1')];
    const { unmatched, allMatched } = computeRenumber(cues);
    expect(unmatched).toHaveLength(1);
    expect(allMatched).toHaveLength(1);
  });

  it('deduplicates same cue_id across multiple lines', () => {
    // cue 1 appears on two lines — should only be counted once
    const cue1 = { ...makeCue(1, '3'), line_id: 100 };
    const cue1dup = { ...makeCue(1, '3'), line_id: 200 };
    const cue2 = makeCue(2, '1');

    const { allMatched, changes } = computeRenumber([cue1, cue1dup, cue2]);
    expect(allMatched).toHaveLength(2);
    // "1"→"1" no change; "3"→"2" is a change
    expect(changes).toHaveLength(1);
    expect(changes[0].oldIdent).toBe('3');
    expect(changes[0].newIdent).toBe('2');
  });

  it('sorts by float value, not lexicographic', () => {
    const cues = ['10', '2', '1'].map((ident, i) => makeCue(i, ident));
    const { allMatched } = computeRenumber(cues);
    // sorted by parseFloat: 1, 2, 10 → get idents 1, 2, 3
    const originalIdents = allMatched.map((m) => m.cue.ident);
    expect(originalIdents).toEqual(['1', '2', '10']);
  });

  it('maps old ident to new ident correctly in changes', () => {
    // "1" sorts to position 1 → computedIdent "1" (no change)
    // "2.1" sorts to position 2 → computedIdent "2" (change)
    const cues = [makeCue(1, '2.1'), makeCue(2, '1')];
    const { changes } = computeRenumber(cues);
    expect(changes).toHaveLength(1);
    expect(changes[0].oldIdent).toBe('2.1');
    expect(changes[0].newIdent).toBe('2');
  });

  it('cue already at correct position does not appear in changes', () => {
    const cues = [makeCue(1, '2.1'), makeCue(2, '1')];
    const { changes } = computeRenumber(cues);
    const identOneInChanges = changes.find((c) => c.oldIdent === '1');
    expect(identOneInChanges).toBeUndefined();
  });

  it('handles MagicQ renumber example correctly', () => {
    const idents = ['1', '2', '2.1', '2.2', '3', '4', '4.1', '4.2', '5'];
    const cues = idents.map((ident, i) => makeCue(i, ident));
    const { allMatched, changes } = computeRenumber(cues);

    expect(allMatched.map((m) => m.computedIdent)).toEqual([
      '1',
      '2',
      '3',
      '4',
      '5',
      '6',
      '7',
      '8',
      '9',
    ]);
    // All except the first (1→1) should be in changes
    expect(changes.length).toBe(7);
  });

  it('places text-suffix cue in unmatched with pre-computed slot ident', () => {
    // Tim's example: 1, 2, 2.1 - Blackout, 3 → 1, 2, 3 - Blackout, 4
    const cues = [makeCue(1, '1'), makeCue(2, '2'), makeCue(3, '2.1 - Blackout'), makeCue(4, '3')];
    const { allMatched, changes, unmatched } = computeRenumber(cues);

    // Slots: "1"→slot1, "2"→slot2, "2.1 - Blackout"→slot3, "3"→slot4
    expect(allMatched).toHaveLength(3); // only fully numeric
    expect(allMatched.map((m) => m.computedIdent)).toEqual(['1', '2', '4']);

    expect(changes).toHaveLength(1); // "3" → "4"
    expect(changes[0].oldIdent).toBe('3');
    expect(changes[0].newIdent).toBe('4');

    expect(unmatched).toHaveLength(1);
    expect(unmatched[0].originalIdent).toBe('2.1 - Blackout');
    expect(unmatched[0].newIdent).toBe('3 - Blackout');
    expect(unmatched[0].include).toBe(false);
  });

  it('text-suffix cue consumes a slot, shifting later pure cues', () => {
    const cues = [makeCue(1, '1 - House'), makeCue(2, '53'), makeCue(3, '56')];
    const { allMatched, changes, unmatched } = computeRenumber(cues);

    // "1 - House" takes slot 1, so "53"→slot2="2", "56"→slot3="3"
    expect(allMatched.map((m) => m.computedIdent)).toEqual(['2', '3']);
    expect(changes).toHaveLength(2);
    expect(unmatched).toHaveLength(1);
    expect(unmatched[0].newIdent).toBe('1 - House');
  });

  it('fully non-numeric cue goes to unmatched with empty newIdent', () => {
    const cues = [makeCue(1, 'LX-INTRO'), makeCue(2, '1')];
    const { allMatched, unmatched } = computeRenumber(cues);

    expect(allMatched).toHaveLength(1);
    expect(unmatched).toHaveLength(1);
    expect(unmatched[0].newIdent).toBe('');
  });
});

describe('useCueRenumber / flattenCuesForType', () => {
  it('extracts cues for the given type from the cues dict', () => {
    const { flattenCuesForType } = useCueRenumber();
    const cues: Record<string, Cue[]> = {
      '10': [
        {
          id: 1,
          cue_type_id: 1,
          ident: 'A',
          group_id: null,
          sort_order: null,
          line_position: null,
        },
        {
          id: 2,
          cue_type_id: 2,
          ident: 'B',
          group_id: null,
          sort_order: null,
          line_position: null,
        },
      ],
      '20': [
        {
          id: 3,
          cue_type_id: 1,
          ident: 'C',
          group_id: null,
          sort_order: null,
          line_position: null,
        },
      ],
    };

    const result = flattenCuesForType(cues, 1);
    expect(result).toHaveLength(2);
    expect(result.map((c) => c.id)).toEqual([1, 3]);
    expect(result.find((c) => c.id === 1)?.line_id).toBe(10);
    expect(result.find((c) => c.id === 3)?.line_id).toBe(20);
  });

  it('returns empty array when no cues match the type', () => {
    const { flattenCuesForType } = useCueRenumber();
    const cues: Record<string, Cue[]> = {
      '10': [
        {
          id: 1,
          cue_type_id: 2,
          ident: 'A',
          group_id: null,
          sort_order: null,
          line_position: null,
        },
      ],
    };
    expect(flattenCuesForType(cues, 1)).toHaveLength(0);
  });

  it('returns empty array for empty cues dict', () => {
    const { flattenCuesForType } = useCueRenumber();
    expect(flattenCuesForType({}, 1)).toHaveLength(0);
  });
});
