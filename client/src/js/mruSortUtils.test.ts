import { describe, it, expect } from 'vitest';
import { buildMruCharacterOptions, buildMruCharacterGroupOptions } from './mruSortUtils';

const CHARS = [
  { id: 1, name: 'Alice' },
  { id: 2, name: 'Bob' },
  { id: 3, name: 'Carol' },
];

const GROUPS = [
  { id: 10, name: 'Ensemble' },
  { id: 11, name: 'Chorus' },
];

function makePage(
  entries: Array<{ character_id?: number | null; character_group_id?: number | null }>
) {
  return entries.map((e) => ({ line_parts: [e] }));
}

describe('buildMruCharacterOptions', () => {
  it('returns null when tmpScript is empty', () => {
    expect(buildMruCharacterOptions(CHARS, {})).toBeNull();
  });

  it('returns null when no line parts have a character_id set', () => {
    const script = { '1': makePage([{ character_id: null }, { character_group_id: 10 }]) };
    expect(buildMruCharacterOptions(CHARS, script)).toBeNull();
  });

  it('sorts characters by descending frequency', () => {
    const script = {
      '1': makePage([{ character_id: 2 }, { character_id: 2 }, { character_id: 1 }]),
    };
    const result = buildMruCharacterOptions(CHARS, script)!;
    const ids = result.slice(1).map((o) => o.value);
    expect(ids).toEqual([2, 1, 3]);
  });

  it('always prepends the N/A null option', () => {
    const script = { '1': makePage([{ character_id: 1 }]) };
    const result = buildMruCharacterOptions(CHARS, script)!;
    expect(result[0]).toEqual({ value: null, text: 'N/A' });
  });

  it('preserves original order for characters with equal frequency', () => {
    const script = {
      '1': makePage([{ character_id: 1 }, { character_id: 2 }]),
    };
    const result = buildMruCharacterOptions(CHARS, script)!;
    const ids = result.slice(1).map((o) => o.value);
    expect(ids).toEqual([1, 2, 3]);
  });

  it('places characters absent from script after those that appear', () => {
    const script = { '1': makePage([{ character_id: 3 }]) };
    const result = buildMruCharacterOptions(CHARS, script)!;
    const ids = result.slice(1).map((o) => o.value);
    expect(ids[0]).toBe(3);
  });

  it('aggregates counts across multiple pages', () => {
    const script = {
      '1': makePage([{ character_id: 1 }]),
      '2': makePage([{ character_id: 2 }, { character_id: 2 }]),
      '3': makePage([{ character_id: 1 }]),
    };
    const result = buildMruCharacterOptions(CHARS, script)!;
    const ids = result.slice(1).map((o) => o.value);
    // Bob (2): count 2, Alice (1): count 2, Carol: 0 — equal count keeps original order
    expect(ids).toEqual([1, 2, 3]);
  });

  it('handles lines with no line_parts gracefully', () => {
    const script = { '1': [{ line_parts: undefined as any }, { line_parts: [] }] };
    expect(buildMruCharacterOptions(CHARS, script)).toBeNull();
  });
});

describe('buildMruCharacterGroupOptions', () => {
  it('returns null when tmpScript is empty', () => {
    expect(buildMruCharacterGroupOptions(GROUPS, {})).toBeNull();
  });

  it('returns null when no line parts have a character_group_id set', () => {
    const script = { '1': makePage([{ character_id: 1 }]) };
    expect(buildMruCharacterGroupOptions(GROUPS, script)).toBeNull();
  });

  it('sorts groups by descending frequency', () => {
    const script = {
      '1': makePage([
        { character_group_id: 11 },
        { character_group_id: 11 },
        { character_group_id: 10 },
      ]),
    };
    const result = buildMruCharacterGroupOptions(GROUPS, script)!;
    const ids = result.slice(1).map((o) => o.value);
    expect(ids).toEqual([11, 10]);
  });

  it('always prepends the N/A null option', () => {
    const script = { '1': makePage([{ character_group_id: 10 }]) };
    const result = buildMruCharacterGroupOptions(GROUPS, script)!;
    expect(result[0]).toEqual({ value: null, text: 'N/A' });
  });

  it('aggregates counts across multiple pages', () => {
    const script = {
      '1': makePage([{ character_group_id: 10 }]),
      '2': makePage([{ character_group_id: 11 }, { character_group_id: 11 }]),
    };
    const result = buildMruCharacterGroupOptions(GROUPS, script)!;
    const ids = result.slice(1).map((o) => o.value);
    expect(ids).toEqual([11, 10]);
  });
});
