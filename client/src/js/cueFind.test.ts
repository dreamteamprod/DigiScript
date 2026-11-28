import { describe, it, expect } from 'vitest';
import { mergeFindResponses, parseFindQuery, type FindMatch } from './cueFind';
import type { CueType } from '@/types/api/cues';

const type = (id: number, prefix: string): CueType => ({
  id,
  show_id: 1,
  prefix,
  description: null,
  colour: '#fff',
});
const LX = type(1, 'LX');
const SND = type(2, 'SND');
const LXS = type(3, 'LXS');
const types = [LX, SND, LXS];

describe('parseFindQuery', () => {
  it('splits prefix and number, ignoring case and spacing', () => {
    expect(parseFindQuery('LX 13.5', types)).toEqual({
      kind: 'search',
      types: [LX],
      number: '13.5',
    });
    expect(parseFindQuery('  snd7 ', types)).toEqual({ kind: 'search', types: [SND], number: '7' });
  });

  it('uses the longest matching prefix', () => {
    expect(parseFindQuery('LXS 4', types)).toMatchObject({ types: [LXS], number: '4' });
  });

  it('asks which type a bare number is', () => {
    expect(parseFindQuery('13', types)).toEqual({ kind: 'needs-type', number: '13' });
  });

  it('asks for a number when only a prefix is typed', () => {
    expect(parseFindQuery('LX', types)).toEqual({ kind: 'needs-number', types: [LX] });
    expect(parseFindQuery('lx   ', types)).toEqual({ kind: 'needs-number', types: [LX] });
  });

  it('searches every type that shares the prefix', () => {
    const other = type(9, 'lx');
    const result = parseFindQuery('LX 1', [LX, other]);
    expect(result).toMatchObject({ kind: 'search', number: '1' });
    expect((result as { types: CueType[] }).types).toEqual([LX, other]);
  });

  it('treats blank input as empty', () => {
    expect(parseFindQuery('   ', types)).toEqual({ kind: 'empty' });
  });
});

describe('mergeFindResponses', () => {
  const match = (id: number, score?: number): FindMatch => ({
    cue: { id, ident: String(id), cue_type_id: 1 },
    cue_type: LX,
    location: { page: 1, line_id: id, act_id: 1, scene_id: 1 },
    similarity_score: score,
  });

  it('merges exact matches and keeps the best five suggestions by score', () => {
    const merged = mergeFindResponses([
      { exact_matches: [match(1)], suggestions: [match(10, 0.4), match(11, 0.9)] },
      {
        exact_matches: [match(2)],
        suggestions: [match(12, 0.5), match(13, 0.6), match(14, 0.7), match(15, 0.8)],
      },
    ]);
    expect(merged.exact_matches.map((m) => m.cue.id)).toEqual([1, 2]);
    expect(merged.suggestions.map((m) => m.cue.id)).toEqual([11, 15, 14, 13, 12]);
  });
});
