import { describe, expect, it } from 'vitest';
import {
  NUMERIC_IDENT_REGEX,
  NUMERIC_PREFIX_REGEX,
  parseMagicQCsv,
  computeRenumber,
  flattenCuesForType,
} from './cueRenumberUtils';
import type { CueWithLineId } from './cueRenumberUtils';
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

/** Builds the sequential mapping that MagicQ would produce for a given set of ident strings. */
function makeMap(idents: string[]): Map<number, number> {
  const floats = idents.map(parseFloat).sort((a, b) => a - b);
  const map = new Map<number, number>();
  floats.forEach((f, i) => map.set(f, i + 1));
  return map;
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

describe('parseMagicQCsv', () => {
  it('builds sequential mapping from Cue id column', () => {
    const csv = `Status ,Cue id ,Cue text ,Comment\n*   ,1.00 ,0001 ,First\n    ,2.10 ,0002 ,Second\n    ,3.00 ,0003 ,Third`;
    const mapping = parseMagicQCsv(csv);
    expect(mapping.get(1)).toBe(1);
    expect(mapping.get(2.1)).toBe(2);
    expect(mapping.get(3)).toBe(3);
    expect(mapping.size).toBe(3);
  });

  it('finds Cue id column by header name regardless of column position', () => {
    const csv = `Comment ,Cue id ,Status\nFirst ,1.00 ,*\nSecond ,2.00 ,`;
    const mapping = parseMagicQCsv(csv);
    expect(mapping.size).toBe(2);
    expect(mapping.get(1)).toBe(1);
    expect(mapping.get(2)).toBe(2);
  });

  it('assigns sequential integers in sort order, not CSV order', () => {
    const csv = `Status ,Cue id ,Comment\n,3.00 ,third\n,1.00 ,first\n,2.00 ,second`;
    const mapping = parseMagicQCsv(csv);
    expect(mapping.get(1)).toBe(1);
    expect(mapping.get(2)).toBe(2);
    expect(mapping.get(3)).toBe(3);
  });

  it('trims whitespace from header and values', () => {
    const csv = `Status , Cue id , Comment\n*   , 1.00 ,comment\n    , 2.10 ,comment`;
    const mapping = parseMagicQCsv(csv);
    expect(mapping.get(1)).toBe(1);
    expect(mapping.get(2.1)).toBe(2);
  });

  it('skips rows with non-numeric cue id values', () => {
    const csv = `Status ,Cue id ,Comment\n,1.00 ,ok\n,text ,skip\n,2.00 ,ok`;
    const mapping = parseMagicQCsv(csv);
    expect(mapping.size).toBe(2);
  });

  it('skips rows that are too short', () => {
    const csv = `Status ,Cue id ,Comment\n,1.00 ,ok\nshortrow\n,2.00 ,ok`;
    const mapping = parseMagicQCsv(csv);
    expect(mapping.size).toBe(2);
  });

  it('returns empty map when Cue id column not found', () => {
    const csv = `Status ,Cue ,Comment\n,1.00 ,text`;
    expect(parseMagicQCsv(csv).size).toBe(0);
  });

  it('returns empty map for empty string', () => {
    expect(parseMagicQCsv('').size).toBe(0);
  });

  it('handles the real MagicQ export format', () => {
    const csv = `Status ,Cue id ,Cue text ,Wait ,Halt ,Delay ,Fade ,Pos ,Col ,Beam ,Cue ,Next cue ,Timing ,Track ,Block FX ,Cue only ,Macro ,Comment ,Audio ,Media\n*   ,1.00 ,0001 ,00/00/05.23 ,Tc , 0.00s , 0.00s ,0.00s ,0.00s ,0.00s ,Q1(L)0001 ,Next ,Cue ,HLF ,No ,No , ,Lights On , ,\n    ,2.00 ,0002 ,00/00/06.02 ,Tc , 0.00s , 0.00s ,0.00s ,0.00s ,0.00s ,Q2(L)0002 ,Next ,Cue ,HLF ,No ,No , ,Lights Off , ,`;
    const mapping = parseMagicQCsv(csv);
    expect(mapping.get(1)).toBe(1);
    expect(mapping.get(2)).toBe(2);
  });
});

describe('computeRenumber', () => {
  it('assigns sequential integers sorted by parseFloat', () => {
    const cues = ['2.1', '1', '3', '2', '2.2'].map((ident, i) => makeCue(i, ident));
    const csvMapping = makeMap(['2.1', '1', '3', '2', '2.2']);
    const { allMatched, changes } = computeRenumber(cues, csvMapping);

    expect(allMatched.map((m) => m.computedIdent)).toEqual(['1', '2', '3', '4', '5']);
    // "1"→"1" and "2"→"2" stay the same; "2.1"→"3", "2.2"→"4", "3"→"5" change
    expect(changes).toHaveLength(3);
  });

  it('returns empty changes when cues are already sequential', () => {
    const cues = ['1', '2', '3'].map((ident, i) => makeCue(i, ident));
    const csvMapping = makeMap(['1', '2', '3']);
    const { allMatched, changes } = computeRenumber(cues, csvMapping);

    expect(changes).toHaveLength(0);
    expect(allMatched).toHaveLength(3);
    expect(allMatched.map((m) => m.computedIdent)).toEqual(['1', '2', '3']);
  });

  it('allMatched contains ALL matched cues including unchanged ones', () => {
    const cues = ['1', '2', '3'].map((ident, i) => makeCue(i, ident));
    const { allMatched } = computeRenumber(cues, makeMap(['1', '2', '3']));
    expect(allMatched).toHaveLength(3);
  });

  it('separates non-numeric idents into unmatched', () => {
    const cues = [makeCue(1, '1'), makeCue(2, 'LX-INTRO'), makeCue(3, '2'), makeCue(4, '')];
    const { allMatched, changes, unmatched } = computeRenumber(cues, makeMap(['1', '2']));

    expect(allMatched).toHaveLength(2);
    expect(changes).toHaveLength(0);
    expect(unmatched).toHaveLength(2);
    expect(unmatched.every((u) => !u.include)).toBe(true);
    expect(unmatched.every((u) => u.newIdent === '')).toBe(true);
  });

  it('treats null ident as unmatched', () => {
    const cues = [makeCue(1, null), makeCue(2, '1')];
    const { unmatched, allMatched } = computeRenumber(cues, makeMap(['1']));
    expect(unmatched).toHaveLength(1);
    expect(allMatched).toHaveLength(1);
  });

  it('deduplicates same cue_id across multiple lines', () => {
    const cue1 = { ...makeCue(1, '3'), line_id: 100 };
    const cue1dup = { ...makeCue(1, '3'), line_id: 200 };
    const cue2 = makeCue(2, '1');

    const { allMatched, changes } = computeRenumber([cue1, cue1dup, cue2], makeMap(['3', '1']));
    expect(allMatched).toHaveLength(2);
    // "1"→"1" no change; "3"→"2" is a change
    expect(changes).toHaveLength(1);
    expect(changes[0].oldIdent).toBe('3');
    expect(changes[0].newIdent).toBe('2');
  });

  it('sorts by float value, not lexicographic', () => {
    const cues = ['10', '2', '1'].map((ident, i) => makeCue(i, ident));
    const { allMatched } = computeRenumber(cues, makeMap(['10', '2', '1']));
    const originalIdents = allMatched.map((m) => m.cue.ident);
    expect(originalIdents).toEqual(['1', '2', '10']);
  });

  it('maps old ident to new ident correctly in changes', () => {
    const cues = [makeCue(1, '2.1'), makeCue(2, '1')];
    const { changes } = computeRenumber(cues, makeMap(['2.1', '1']));
    expect(changes).toHaveLength(1);
    expect(changes[0].oldIdent).toBe('2.1');
    expect(changes[0].newIdent).toBe('2');
  });

  it('cue already at correct position does not appear in changes', () => {
    const cues = [makeCue(1, '2.1'), makeCue(2, '1')];
    const { changes } = computeRenumber(cues, makeMap(['2.1', '1']));
    const identOneInChanges = changes.find((c) => c.oldIdent === '1');
    expect(identOneInChanges).toBeUndefined();
  });

  it('handles MagicQ renumber example correctly', () => {
    const idents = ['1', '2', '2.1', '2.2', '3', '4', '4.1', '4.2', '5'];
    const cues = idents.map((ident, i) => makeCue(i, ident));
    const { allMatched, changes } = computeRenumber(cues, makeMap(idents));

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
    expect(changes.length).toBe(7);
  });

  it('places text-suffix cue in unmatched with pre-computed slot ident', () => {
    // Tim's example: 1, 2, 2.1 - Blackout, 3 → 1, 2, 3 - Blackout, 4
    const csvMapping = makeMap(['1', '2', '2.1', '3']);
    const cues = [makeCue(1, '1'), makeCue(2, '2'), makeCue(3, '2.1 - Blackout'), makeCue(4, '3')];
    const { allMatched, changes, unmatched } = computeRenumber(cues, csvMapping);

    expect(allMatched).toHaveLength(3);
    expect(allMatched.map((m) => m.computedIdent)).toEqual(['1', '2', '4']);

    expect(changes).toHaveLength(1);
    expect(changes[0].oldIdent).toBe('3');
    expect(changes[0].newIdent).toBe('4');

    expect(unmatched).toHaveLength(1);
    expect(unmatched[0].originalIdent).toBe('2.1 - Blackout');
    expect(unmatched[0].newIdent).toBe('3 - Blackout');
    expect(unmatched[0].include).toBe(false);
  });

  it('text-suffix cue consumes a slot in the CSV, shifting later pure cues', () => {
    // CSV has 1, 53, 56 — "1 - House" in DigiScript matches CSV cue 1
    const csvMapping = makeMap(['1', '53', '56']);
    const cues = [makeCue(1, '1 - House'), makeCue(2, '53'), makeCue(3, '56')];
    const { allMatched, changes, unmatched } = computeRenumber(cues, csvMapping);

    expect(allMatched.map((m) => m.computedIdent)).toEqual(['2', '3']);
    expect(changes).toHaveLength(2);
    expect(unmatched).toHaveLength(1);
    expect(unmatched[0].newIdent).toBe('1 - House');
  });

  it('fully non-numeric cue goes to unmatched with empty newIdent', () => {
    const cues = [makeCue(1, 'LX-INTRO'), makeCue(2, '1')];
    const { allMatched, unmatched } = computeRenumber(cues, makeMap(['1']));

    expect(allMatched).toHaveLength(1);
    expect(unmatched).toHaveLength(1);
    expect(unmatched[0].newIdent).toBe('');
  });

  it('cue with numeric prefix absent from CSV goes to unmatched with empty newIdent', () => {
    // DigiScript has cues 1 and 5, but CSV only has 1, 2, 3 (cue 5 is not in the console export)
    const csvMapping = new Map<number, number>([
      [1, 1],
      [2, 2],
      [3, 3],
    ]);
    const cues = [makeCue(1, '1'), makeCue(2, '5')];
    const { allMatched, unmatched } = computeRenumber(cues, csvMapping);

    expect(allMatched).toHaveLength(1);
    expect(allMatched[0].computedIdent).toBe('1');
    expect(unmatched).toHaveLength(1);
    expect(unmatched[0].originalIdent).toBe('5');
    expect(unmatched[0].newIdent).toBe('');
  });

  it('correctly handles sparse DigiScript cues against a full CSV', () => {
    // Console has 1, 2, 2.1, 3, 4 — DigiScript only has 1 and 3
    // After renum: 1→1, 2→2, 2.1→3, 3→4, 4→5 — so DigiScript's "3" should become "4"
    const csvMapping = makeMap(['1', '2', '2.1', '3', '4']);
    const cues = [makeCue(1, '1'), makeCue(2, '3')];
    const { allMatched, changes } = computeRenumber(cues, csvMapping);

    expect(allMatched.map((m) => m.computedIdent)).toEqual(['1', '4']);
    expect(changes).toHaveLength(1);
    expect(changes[0].oldIdent).toBe('3');
    expect(changes[0].newIdent).toBe('4');
  });
});

describe('flattenCuesForType', () => {
  it('extracts cues for the given type from the cues dict', () => {
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
    expect(flattenCuesForType({}, 1)).toHaveLength(0);
  });
});
