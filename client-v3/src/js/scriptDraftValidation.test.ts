import { describe, it, expect } from 'vitest';
import { validateDraftLine, firstInvalidDraftLine } from './scriptDraftValidation';
import { LINE_TYPES } from '@/constants/lineTypes';
import type { DraftScriptLine, DraftScriptLinePart } from './yjs/draftAdapter';
import type { LineUid, PartUid } from './yjs/yjsSnapshot';

function part(overrides: Partial<DraftScriptLinePart> = {}): DraftScriptLinePart {
  return {
    _id: 'p1',
    _uid: 'p1' as PartUid,
    id: null,
    line_id: null,
    part_index: 0,
    character_id: null,
    character_group_id: null,
    line_text: '',
    ...overrides,
  };
}

function line(overrides: Partial<DraftScriptLine> = {}): DraftScriptLine {
  return {
    _id: 'l1',
    _uid: 'l1' as LineUid,
    id: null,
    act_id: 1,
    scene_id: 1,
    page: 1,
    line_type: LINE_TYPES.DIALOGUE,
    stage_direction_style_id: null,
    line_parts: [],
    ...overrides,
  };
}

describe('validateDraftLine', () => {
  it('rejects a missing act or scene regardless of line type', () => {
    expect(validateDraftLine(line({ act_id: null }), false).isValid).toBe(false);
    expect(validateDraftLine(line({ scene_id: null }), false).isValid).toBe(false);
  });

  describe('dialogue', () => {
    it('accepts a single part with a character and text', () => {
      const result = validateDraftLine(
        line({ line_parts: [part({ character_id: 1, line_text: 'Hi' })] }),
        false
      );
      expect(result).toEqual({ isValid: true, error: '' });
    });

    it('accepts a character group instead of a character', () => {
      const result = validateDraftLine(
        line({ line_parts: [part({ character_group_id: 1, line_text: 'Hi' })] }),
        false
      );
      expect(result.isValid).toBe(true);
    });

    it('rejects zero line parts', () => {
      const result = validateDraftLine(line({ line_parts: [] }), false);
      expect(result).toEqual({
        isValid: false,
        error: 'Dialogue lines must have at least one line part',
      });
    });

    it('rejects more than one part in compact mode', () => {
      const result = validateDraftLine(
        line({
          line_parts: [
            part({ character_id: 1, line_text: 'a' }),
            part({ character_id: 2, line_text: 'b' }),
          ],
        }),
        true
      );
      expect(result).toEqual({
        isValid: false,
        error: 'Lines can only have 1 line part in compact script mode',
      });
    });

    it('allows multiple parts outside compact mode', () => {
      const result = validateDraftLine(
        line({
          line_parts: [
            part({ character_id: 1, line_text: 'a' }),
            part({ character_id: 2, line_text: 'b' }),
          ],
        }),
        false
      );
      expect(result.isValid).toBe(true);
    });

    it('rejects a part with neither character nor group', () => {
      const result = validateDraftLine(line({ line_parts: [part({ line_text: 'Hi' })] }), false);
      expect(result).toEqual({
        isValid: false,
        error: 'Dialogue line parts must have a character or character group',
      });
    });

    it('rejects a part with both character and group', () => {
      const result = validateDraftLine(
        line({
          line_parts: [part({ character_id: 1, character_group_id: 1, line_text: 'Hi' })],
        }),
        false
      );
      expect(result).toEqual({
        isValid: false,
        error: 'Line parts cannot have both character and character group',
      });
    });

    it('rejects empty text on a single part', () => {
      const result = validateDraftLine(
        line({ line_parts: [part({ character_id: 1, line_text: '' })] }),
        false
      );
      expect(result).toEqual({ isValid: false, error: 'Dialogue lines must contain text' });
    });

    it('allows one empty part if another part has text', () => {
      const result = validateDraftLine(
        line({
          line_parts: [
            part({ character_id: 1, line_text: '' }),
            part({ character_id: 2, line_text: 'Hi' }),
          ],
        }),
        false
      );
      expect(result.isValid).toBe(true);
    });

    it('rejects all-empty text across multiple parts', () => {
      const result = validateDraftLine(
        line({
          line_parts: [
            part({ character_id: 1, line_text: '' }),
            part({ character_id: 2, line_text: '' }),
          ],
        }),
        false
      );
      expect(result).toEqual({ isValid: false, error: 'At least one line part must contain text' });
    });
  });

  describe('stage direction', () => {
    const stageLine = (overrides: Partial<DraftScriptLinePart> = {}) =>
      line({ line_type: LINE_TYPES.STAGE_DIRECTION, line_parts: [part(overrides)] });

    it('accepts one part with text', () => {
      expect(validateDraftLine(stageLine({ line_text: 'He walks' }), false).isValid).toBe(true);
    });

    it('rejects zero parts', () => {
      const result = validateDraftLine(
        line({ line_type: LINE_TYPES.STAGE_DIRECTION, line_parts: [] }),
        false
      );
      expect(result).toEqual({
        isValid: false,
        error: 'Stage directions must have exactly 1 line part',
      });
    });

    it('rejects more than one part', () => {
      const result = validateDraftLine(
        line({
          line_type: LINE_TYPES.STAGE_DIRECTION,
          line_parts: [part({ line_text: 'a' }), part({ line_text: 'b' })],
        }),
        false
      );
      expect(result.isValid).toBe(false);
    });

    it('rejects both character and group on its one part', () => {
      const result = validateDraftLine(
        stageLine({ character_id: 1, character_group_id: 1, line_text: 'He walks' }),
        false
      );
      expect(result).toEqual({
        isValid: false,
        error: 'Stage directions cannot have both character and character group',
      });
    });

    it('rejects empty text', () => {
      const result = validateDraftLine(stageLine({ line_text: '' }), false);
      expect(result).toEqual({ isValid: false, error: 'Stage directions must contain text' });
    });

    it('rejects whitespace-only text', () => {
      const result = validateDraftLine(stageLine({ line_text: '   ' }), false);
      expect(result).toEqual({ isValid: false, error: 'Stage directions must contain text' });
    });
  });

  describe('cue line and spacing', () => {
    it('accepts a cue line with no parts', () => {
      const result = validateDraftLine(
        line({ line_type: LINE_TYPES.CUE_LINE, line_parts: [] }),
        false
      );
      expect(result.isValid).toBe(true);
    });

    it('rejects a cue line with a line part', () => {
      const result = validateDraftLine(
        line({ line_type: LINE_TYPES.CUE_LINE, line_parts: [part()] }),
        false
      );
      expect(result).toEqual({ isValid: false, error: 'Cue lines cannot have line parts' });
    });

    it('accepts a spacing line with no parts', () => {
      const result = validateDraftLine(
        line({ line_type: LINE_TYPES.SPACING, line_parts: [] }),
        false
      );
      expect(result.isValid).toBe(true);
    });

    it('rejects a spacing line with a line part', () => {
      const result = validateDraftLine(
        line({ line_type: LINE_TYPES.SPACING, line_parts: [part()] }),
        false
      );
      expect(result).toEqual({ isValid: false, error: 'Spacing lines cannot have line parts' });
    });
  });
});

describe('firstInvalidDraftLine', () => {
  it('returns null when every page is valid', () => {
    const pages = {
      '1': [line({ line_parts: [part({ character_id: 1, line_text: 'Hi' })] })],
      '2': [],
    };
    expect(firstInvalidDraftLine(pages, false)).toBeNull();
  });

  it('finds the first invalid line, scanning pages in numeric order', () => {
    const badOnPage1 = line({ act_id: null });
    const badOnPage10 = line({ scene_id: null });
    // Numeric page-key order (1, 2, 10), not string order (1, 10, 2) — a plain sort
    // would check page "10" before page "2".
    const pages = {
      '10': [badOnPage10],
      '2': [line({ line_parts: [part({ character_id: 1, line_text: 'Hi' })] })],
      '1': [line({ line_parts: [part({ character_id: 1, line_text: 'Hi' })] }), badOnPage1],
    };

    const result = firstInvalidDraftLine(pages, false);

    expect(result?.page).toBe('1');
    expect(result?.line).toBe(badOnPage1);
    expect(result?.error).toBe('Act and scene are required');
  });
});
