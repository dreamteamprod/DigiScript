import { describe, it, expect } from 'vitest';
import { expandWholeRange, parseRangeText, MAX_RANGE_CUES } from './cueRange';

describe('expandWholeRange', () => {
  it('expands an inclusive range of whole numbers', () => {
    expect(expandWholeRange('15', '18')).toEqual(['15', '16', '17', '18']);
    expect(expandWholeRange(' 3 ', '3')).toEqual(['3']);
  });

  it('rejects non-whole numbers, blanks and reversed ranges', () => {
    expect(expandWholeRange('1.5', '3')).toBeNull();
    expect(expandWholeRange('', '3')).toBeNull();
    expect(expandWholeRange('a', '3')).toBeNull();
    expect(expandWholeRange('26', '15')).toBeNull();
  });

  it('allows exactly the maximum and no more', () => {
    expect(expandWholeRange('1', String(MAX_RANGE_CUES))).toHaveLength(MAX_RANGE_CUES);
    expect(expandWholeRange('1', String(MAX_RANGE_CUES + 1))).toBeNull();
  });
});

describe('parseRangeText (live view syntax)', () => {
  it('keeps the "a > b" syntax working', () => {
    expect(parseRangeText('1 > 3')).toEqual(['1', '2', '3']);
    expect(parseRangeText('1>3')).toEqual(['1', '2', '3']);
    expect(parseRangeText('3 > 1')).toBeNull();
    expect(parseRangeText('1-3')).toBeNull();
  });
});
