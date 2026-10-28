import { LINE_TYPES } from '@/constants/lineTypes';
import type { DraftScriptLine, DraftScriptLinePart } from './yjs/draftAdapter';

/**
 * Discriminated on `isValid` so `{ isValid: true, error: 'something' }` and
 * `{ isValid: false, error: '' }` are both unrepresentable — a caller can only
 * read `.error` once `.isValid` has narrowed to `false`.
 */
export type LineValidationResult =
  | { isValid: true }
  | {
      isValid: false;
      /** Why the line failed, for Save's disabled-reason and a SAVE_ERROR-shaped message. */
      error: string;
    };

const VALID: LineValidationResult = { isValid: true };

function invalid(error: string): LineValidationResult {
  return { isValid: false, error };
}

function hasText(part: DraftScriptLinePart): boolean {
  return part.line_text != null && part.line_text !== '';
}

/**
 * Mirrors `utils/show/line_type_validator.py` — kept in sync by hand since there is no
 * shared source between the two languages (see the cross-language fixture test for the
 * writer's own structural guarantee, which this is not). One real difference: the
 * server's dialogue "must contain text" checks are `is None` only, which an
 * always-a-string `Y.Text` can never trigger — this validator checks for an *empty*
 * string instead, matching the classic editor's own (also client-only) convention, so
 * Save disables itself for an empty line exactly as it always has, rather than letting
 * the collab draft save one the server would technically accept.
 */
/** Null when `part`'s text is fine; otherwise the reason it isn't. */
function dialoguePartTextError(
  part: DraftScriptLinePart,
  isOnlyPart: boolean,
  anyPartHasText: boolean
): string | null {
  if (hasText(part)) return null;
  if (isOnlyPart) return 'Dialogue lines must contain text';
  if (!anyPartHasText) return 'At least one line part must contain text';
  return null;
}

/** Null when `part`'s character/group assignment is fine; otherwise the reason it isn't. */
function partCharacterError(part: DraftScriptLinePart): string | null {
  const hasCharacter = part.character_id != null;
  const hasGroup = part.character_group_id != null;
  if (!hasCharacter && !hasGroup) {
    return 'Dialogue line parts must have a character or character group';
  }
  if (hasCharacter && hasGroup) {
    return 'Line parts cannot have both character and character group';
  }
  return null;
}

function validateDialogue(line: DraftScriptLine, isCompactMode: boolean): LineValidationResult {
  const parts = line.line_parts;
  if (parts.length === 0) return invalid('Dialogue lines must have at least one line part');
  if (isCompactMode && parts.length > 1) {
    return invalid('Lines can only have 1 line part in compact script mode');
  }

  const anyPartHasText = parts.some(hasText);
  for (const part of parts) {
    const textError = dialoguePartTextError(part, parts.length === 1, anyPartHasText);
    if (textError) return invalid(textError);
    const characterError = partCharacterError(part);
    if (characterError) return invalid(characterError);
  }
  return VALID;
}

function validateStageDirection(line: DraftScriptLine): LineValidationResult {
  const parts = line.line_parts;
  if (parts.length !== 1) return invalid('Stage directions must have exactly 1 line part');

  const part = parts[0]!;
  if (part.character_id != null && part.character_group_id != null) {
    return invalid('Stage directions cannot have both character and character group');
  }
  // Unlike dialogue's check, the server also rejects whitespace-only text here.
  if (part.line_text == null || part.line_text.trim() === '') {
    return invalid('Stage directions must contain text');
  }
  return VALID;
}

function validateEmptyLine(line: DraftScriptLine, lineTypeName: string): LineValidationResult {
  if (line.line_parts.length > 0) return invalid(`${lineTypeName} lines cannot have line parts`);
  return VALID;
}

/**
 * Validate one draft line against the same rules the server enforces at save time,
 * plus act/scene-required — a client-only nicety with no server backstop (the DB
 * columns are nullable), carried over unchanged from the classic editor's own
 * Vuelidate rules so an incomplete line is caught the same way in both editors.
 */
export function validateDraftLine(
  line: DraftScriptLine,
  isCompactMode: boolean
): LineValidationResult {
  if (line.act_id == null || line.scene_id == null) {
    return invalid('Act and scene are required');
  }
  switch (line.line_type) {
    case LINE_TYPES.DIALOGUE:
      return validateDialogue(line, isCompactMode);
    case LINE_TYPES.STAGE_DIRECTION:
      return validateStageDirection(line);
    case LINE_TYPES.CUE_LINE:
      return validateEmptyLine(line, 'Cue');
    case LINE_TYPES.SPACING:
      return validateEmptyLine(line, 'Spacing');
    default:
      // `line_type` is a plain `number` on the shared `ScriptLine`/`DraftScriptLine`
      // API type (narrowing it to the `LineType` literal union would cascade into
      // the classic editor, which also uses that type) — so this can't be a real
      // exhaustiveness check at compile time. It is one at runtime: a corrupt or
      // future line type this validator doesn't know about must not silently pass
      // as valid, which falling through to VALID here would do.
      return invalid(`Unknown line type: ${line.line_type}`);
  }
}

export interface InvalidDraftLine {
  page: string;
  line: DraftScriptLine;
  error: string;
}

/** The first invalid line across every page of a snapshot record, or null if all are valid. */
export function firstInvalidDraftLine(
  pages: Record<string, DraftScriptLine[]>,
  isCompactMode: boolean
): InvalidDraftLine | null {
  for (const page of Object.keys(pages).sort((a, b) => Number(a) - Number(b))) {
    for (const line of pages[page]!) {
      const result = validateDraftLine(line, isCompactMode);
      if (!result.isValid) return { page, line, error: result.error };
    }
  }
  return null;
}
