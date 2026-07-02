import type { Cue } from '@/types/api/cues';

export const NUMERIC_IDENT_REGEX = /^\d+(\.\d{1,2})?$/;

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
  const matched: CueWithLineId[] = [];
  const unmatched: RenumberUnmatched[] = [];

  for (const cue of uniqueCues) {
    const ident = cue.ident?.trim() ?? '';
    if (NUMERIC_IDENT_REGEX.test(ident)) {
      matched.push(cue);
    } else {
      unmatched.push({ cue, originalIdent: ident, newIdent: '', include: false });
    }
  }

  matched.sort((a, b) => parseFloat(a.ident!) - parseFloat(b.ident!));

  const allMatched: RenumberAllMatched[] = [];
  const changes: RenumberChange[] = [];
  matched.forEach((cue, index) => {
    const computedIdent = String(index + 1);
    allMatched.push({ cue, computedIdent });
    if (cue.ident !== computedIdent) {
      changes.push({ cue, oldIdent: cue.ident ?? '', newIdent: computedIdent });
    }
  });

  return { allMatched, changes, unmatched };
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
