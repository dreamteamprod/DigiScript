import { describe, it, expect } from 'vitest';
import { nextSelectionRange } from './scriptSelectionModel';

describe('nextSelectionRange', () => {
  it('starts a fresh single-line range when nothing is selected', () => {
    expect(nextSelectionRange(null, 4)).toEqual({ startIndex: 4, endIndex: 4 });
  });

  it('extends the start backward when ticking before the range', () => {
    expect(nextSelectionRange({ startIndex: 3, endIndex: 5 }, 1)).toEqual({
      startIndex: 1,
      endIndex: 5,
    });
  });

  it('extends the end forward when ticking after the range', () => {
    expect(nextSelectionRange({ startIndex: 3, endIndex: 5 }, 8)).toEqual({
      startIndex: 3,
      endIndex: 8,
    });
  });

  it('clears the selection when ticking the sole selected line again', () => {
    expect(nextSelectionRange({ startIndex: 4, endIndex: 4 }, 4)).toBeNull();
  });

  it('shrinks the range by removing just the start line, keeping the rest selected', () => {
    expect(nextSelectionRange({ startIndex: 3, endIndex: 6 }, 3)).toEqual({
      startIndex: 4,
      endIndex: 6,
    });
  });

  it('shrinks the range by removing just the end line, keeping the rest selected', () => {
    expect(nextSelectionRange({ startIndex: 3, endIndex: 6 }, 6)).toEqual({
      startIndex: 3,
      endIndex: 5,
    });
  });

  it('shrinking a two-line range from its start leaves a single-line selection', () => {
    expect(nextSelectionRange({ startIndex: 3, endIndex: 4 }, 3)).toEqual({
      startIndex: 4,
      endIndex: 4,
    });
  });

  it('shrinking a two-line range from its end leaves a single-line selection', () => {
    expect(nextSelectionRange({ startIndex: 3, endIndex: 4 }, 4)).toEqual({
      startIndex: 3,
      endIndex: 3,
    });
  });

  it('collapses to just the clicked line when ticking a genuinely interior line', () => {
    expect(nextSelectionRange({ startIndex: 3, endIndex: 7 }, 5)).toEqual({
      startIndex: 5,
      endIndex: 5,
    });
  });
});
