import { describe, it, expect } from 'vitest';
import { computePageStatus } from './scriptConfig';

function makeLine(id, numParts) {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: 1,
    stage_direction_style_id: null,
    line_parts: Array.from({ length: numParts }, (_, i) => ({
      id: id != null ? 100 + i : null,
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
    // deep-object-diff marks index 0 as "added" when a new line_part appears on an existing line.
    // The fix: if the line has an id it must go to updated instead.
    const saved = [makeLine(42, 1)];
    const edited = [makeLine(42, 2)];

    const status = computePageStatus(saved, edited, [], []);

    expect(status.added).not.toContain(0);
    expect(status.updated).toContain(0);
    expect(status.deleted).toHaveLength(0);
    expect(status.inserted).toHaveLength(0);
  });

  it('classifies a genuinely new line (id == null) as added', () => {
    const saved = [];
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
    // Inserted at index 1: augmented actual includes newLine at index 1 so diff sees no change
    const edited = [makeLine(10, 1), newLine];

    const status = computePageStatus(saved, edited, [], [1]);

    expect(status.inserted).toContain(1);
  });

  it('handles a mixed page: one truly-new line and one existing line whose parts grew', () => {
    const saved = [makeLine(42, 1)];
    // Index 0: existing line with extra part; index 1: brand-new line
    const edited = [makeLine(42, 2), makeLine(null, 1)];

    const status = computePageStatus(saved, edited, [], []);

    expect(status.updated).toContain(0);
    expect(status.added).not.toContain(0);
    expect(status.added).toContain(1);
    expect(status.updated).not.toContain(1);
  });

  it('returns all empty arrays when actual and tmp pages are identical', () => {
    const page = [makeLine(42, 2), makeLine(43, 1)];

    const status = computePageStatus(page, JSON.parse(JSON.stringify(page)), [], []);

    expect(status.added).toHaveLength(0);
    expect(status.updated).toHaveLength(0);
    expect(status.deleted).toHaveLength(0);
    expect(status.inserted).toHaveLength(0);
  });
});
