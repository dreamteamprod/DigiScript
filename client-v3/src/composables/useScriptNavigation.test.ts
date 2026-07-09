import { describe, it, expect } from 'vitest';
import type { ScriptLine } from '@/types/api/script';
import { LINE_TYPES } from '@/constants/lineTypes';
import { useScriptNavigation, getPreviousLineAcrossPages } from './useScriptNavigation';

function makeLine(overrides: Partial<ScriptLine> & { id: number; page: number }): ScriptLine {
  return {
    act_id: 1,
    scene_id: 1,
    line_type: LINE_TYPES.DIALOGUE,
    stage_direction_style_id: null,
    line_parts: [
      {
        id: overrides.id * 10,
        line_id: overrides.id,
        part_index: 0,
        character_id: 1,
        character_group_id: null,
        line_text: 'Some line text',
      },
    ],
    ...overrides,
  };
}

function makeSpacingLine(id: number, page: number): ScriptLine {
  return {
    id,
    act_id: 1,
    scene_id: 1,
    page,
    line_type: LINE_TYPES.SPACING,
    stage_direction_style_id: null,
    line_parts: [],
  };
}

describe('getPreviousLineAcrossPages', () => {
  it('returns the previous line on the same page', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const lineB = makeLine({ id: 2, page: 1 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA, lineB] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(getPreviousLineAcrossPages(lineB, getPage)).toBe(lineA);
  });

  it('crosses into the previous page when at the start of the current page', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const lineB = makeLine({ id: 2, page: 2 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA], 2: [lineB] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(getPreviousLineAcrossPages(lineB, getPage)).toBe(lineA);
  });

  it('walks back through multiple empty pages to find content', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const lineB = makeLine({ id: 2, page: 4 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA], 2: [], 3: [], 4: [lineB] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(getPreviousLineAcrossPages(lineB, getPage)).toBe(lineA);
  });

  it('returns null when there is no earlier page', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(getPreviousLineAcrossPages(lineA, getPage)).toBeNull();
  });
});

describe('needsActSceneLabel', () => {
  const { needsActSceneLabel } = useScriptNavigation();

  it('does not need a label when the previous line on the same page is the same act/scene', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const lineB = makeLine({ id: 2, page: 1 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA, lineB] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(needsActSceneLabel(lineB, lineA, [], getPage)).toBe(false);
  });

  it('does not need a label when the scene continues across a page boundary', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const lineB = makeLine({ id: 2, page: 2 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA], 2: [lineB] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(needsActSceneLabel(lineB, lineA, [], getPage)).toBe(false);
  });

  it('does not need a label when a spacing line sits exactly at the page boundary (regression case)', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const spacing = makeSpacingLine(2, 2);
    const lineC = makeLine({ id: 3, page: 2 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA], 2: [spacing, lineC] };
    const getPage = (page: number) => pages[page] ?? [];

    // previousLine as seen by lineC is the spacing line, which must be walked past,
    // crossing back to page 1 to find the true same-scene previous line.
    expect(needsActSceneLabel(lineC, spacing, [], getPage)).toBe(false);
  });

  it('needs a label when crossing pages lands on a genuinely different scene', () => {
    const lineA = makeLine({ id: 1, page: 1, scene_id: 1 });
    const lineB = makeLine({ id: 2, page: 2, scene_id: 2 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA], 2: [lineB] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(needsActSceneLabel(lineB, lineA, [], getPage)).toBe(true);
  });

  it('needs a label when there is no previous line at all', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const getPage = () => [];

    expect(needsActSceneLabel(lineA, null, [], getPage)).toBe(true);
  });
});

describe('needsHeadings', () => {
  const { needsHeadings } = useScriptNavigation();

  it('does not need a character heading when the same character continues across a page boundary', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const lineB = makeLine({ id: 2, page: 2 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA], 2: [lineB] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(needsHeadings(lineB, lineA, [], getPage)).toEqual([false]);
  });

  it('does not need a character heading when the same character continues past a spacing line at the page boundary (regression case)', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const spacing = makeSpacingLine(2, 2);
    const lineC = makeLine({ id: 3, page: 2 });
    const pages: Record<number, ScriptLine[]> = { 1: [lineA], 2: [spacing, lineC] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(needsHeadings(lineC, spacing, [], getPage)).toEqual([false]);
  });

  it('needs a character heading when a spacing line at the page boundary hides a genuine character change', () => {
    const lineA = makeLine({ id: 1, page: 1 });
    const spacing = makeSpacingLine(2, 2);
    const lineC = makeLine({ id: 3, page: 2 });
    lineC.line_parts[0].character_id = 2;
    const pages: Record<number, ScriptLine[]> = { 1: [lineA], 2: [spacing, lineC] };
    const getPage = (page: number) => pages[page] ?? [];

    expect(needsHeadings(lineC, spacing, [], getPage)).toEqual([true]);
  });
});
