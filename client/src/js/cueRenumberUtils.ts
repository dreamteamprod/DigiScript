import type { Cue } from '@/types/api/cues';

export const NUMERIC_IDENT_REGEX = /^\d+(\.\d{1,2})?$/;
// Extracts a leading numeric prefix (up to 2 decimal places) plus any trailing suffix.
export const NUMERIC_PREFIX_REGEX = /^(\d+(?:\.\d{1,2})?)(.*)$/;

export interface CueWithLineId extends Cue {
  line_id: number;
}

export interface RenumberChange {
  cue: CueWithLineId;
  oldIdent: string;
  newIdent: string;
}

export interface RenumberUnmatched {
  cue: CueWithLineId;
  originalIdent: string;
  newIdent: string;
  include: boolean;
}

export interface RenumberAllMatched {
  cue: CueWithLineId;
  computedIdent: string;
}

export interface RenumberResult {
  allMatched: RenumberAllMatched[];
  changes: RenumberChange[];
  unmatched: RenumberUnmatched[];
}

export function computeRenumber(cues: CueWithLineId[]): RenumberResult {
  const uniqueCues = [...new Map(cues.map((c) => [c.id, c])).values()];

  interface ParsedCue {
    cue: CueWithLineId;
    numericValue: number;
    suffix: string;
    isFullyNumeric: boolean;
  }

  const withPrefix: ParsedCue[] = [];
  const fullyUnmatched: RenumberUnmatched[] = [];

  for (const cue of uniqueCues) {
    const ident = cue.ident?.trim() ?? '';
    const match = NUMERIC_PREFIX_REGEX.exec(ident);
    if (match) {
      const suffix = match[2];
      withPrefix.push({
        cue,
        numericValue: parseFloat(match[1]),
        suffix,
        isFullyNumeric: suffix.trim() === '',
      });
    } else {
      fullyUnmatched.push({ cue, originalIdent: ident, newIdent: '', include: false });
    }
  }

  withPrefix.sort((a, b) => a.numericValue - b.numericValue);

  const allMatched: RenumberAllMatched[] = [];
  const changes: RenumberChange[] = [];
  const prefixUnmatched: RenumberUnmatched[] = [];

  withPrefix.forEach(({ cue, suffix, isFullyNumeric }, index) => {
    const newIdent = String(index + 1) + suffix;
    if (isFullyNumeric) {
      allMatched.push({ cue, computedIdent: newIdent });
      if ((cue.ident?.trim() ?? '') !== newIdent) {
        changes.push({ cue, oldIdent: cue.ident ?? '', newIdent });
      }
    } else {
      prefixUnmatched.push({ cue, originalIdent: cue.ident ?? '', newIdent, include: false });
    }
  });

  return { allMatched, changes, unmatched: [...prefixUnmatched, ...fullyUnmatched] };
}

export function flattenCuesForType(
  cues: Record<string, Cue[]>,
  cueTypeId: number
): CueWithLineId[] {
  const result: CueWithLineId[] = [];
  for (const [lineIdStr, cueList] of Object.entries(cues)) {
    const lineId = Number(lineIdStr);
    for (const cue of cueList) {
      if (cue.cue_type_id === cueTypeId) {
        result.push({ ...cue, line_id: lineId });
      }
    }
  }
  return result;
}
