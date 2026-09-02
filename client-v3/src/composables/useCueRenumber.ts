import type { Cue } from '@/types/api/cues';

export const NUMERIC_IDENT_REGEX = /^\d+(\.\d{1,2})?$/;
// Extracts a leading numeric prefix (up to 2 decimal places) plus any trailing suffix.
export const NUMERIC_PREFIX_REGEX = /^(\d+(?:\.\d{1,2})?)(?![\d.])(.*)$/;

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

/**
 * Parses a MagicQ cue stack CSV export and returns a mapping from each
 * cue's pre-renum numeric ID (as a float) to its post-renum sequential integer.
 * The "Cue id" column is located by scanning the header row.
 * Returns an empty Map if the column cannot be found or the text is empty.
 */
export function parseMagicQCsv(csvText: string): Map<number, number> {
  const lines = csvText.split('\n');
  if (lines.length === 0) return new Map();

  const headerCols = lines[0].split(',').map((c) => c.trim().toLowerCase());
  const cueIdIdx = headerCols.indexOf('cue id');
  if (cueIdIdx === -1) return new Map();

  const ids: number[] = [];
  for (const line of lines.slice(1)) {
    const cols = line.split(',');
    if (cols.length <= cueIdIdx) continue;
    const val = parseFloat(cols[cueIdIdx].trim());
    if (!isNaN(val)) ids.push(val);
  }

  ids.sort((a, b) => a - b);
  const map = new Map<number, number>();
  ids.forEach((id, i) => map.set(id, i + 1));
  return map;
}

/**
 * Computes renumber suggestions for a set of cues given a CSV-derived mapping.
 * csvMapping maps each pre-renum cue ID (float) to its post-renum sequential integer.
 * Cues whose numeric prefix is not present in the mapping go to unmatched with no suggestion.
 */
export function computeRenumber(
  cues: CueWithLineId[],
  csvMapping: Map<number, number>
): RenumberResult {
  const uniqueCues = [...new Map(cues.map((c) => [c.id, c])).values()];

  interface ParsedCue {
    cue: CueWithLineId;
    numericValue: number;
    suffix: string;
  }

  const withPrefix: ParsedCue[] = [];
  const fullyUnmatched: RenumberUnmatched[] = [];

  for (const cue of uniqueCues) {
    const ident = cue.ident?.trim() ?? '';
    const match = NUMERIC_PREFIX_REGEX.exec(ident);
    if (match) {
      withPrefix.push({ cue, numericValue: parseFloat(match[1]), suffix: match[2] });
    } else {
      fullyUnmatched.push({ cue, originalIdent: ident, newIdent: '', include: false });
    }
  }

  withPrefix.sort((a, b) => a.numericValue - b.numericValue);

  const allMatched: RenumberAllMatched[] = [];
  const changes: RenumberChange[] = [];
  const prefixUnmatched: RenumberUnmatched[] = [];

  for (const { cue, numericValue, suffix } of withPrefix) {
    const newInteger = csvMapping.get(numericValue);
    if (newInteger === undefined) {
      fullyUnmatched.push({ cue, originalIdent: cue.ident ?? '', newIdent: '', include: false });
      continue;
    }
    const newIdent = String(newInteger) + suffix;
    if (suffix.trim() === '') {
      allMatched.push({ cue, computedIdent: newIdent });
      if ((cue.ident?.trim() ?? '') !== newIdent) {
        changes.push({ cue, oldIdent: cue.ident ?? '', newIdent });
      }
    } else {
      prefixUnmatched.push({ cue, originalIdent: cue.ident ?? '', newIdent, include: false });
    }
  }

  return { allMatched, changes, unmatched: [...prefixUnmatched, ...fullyUnmatched] };
}

export function useCueRenumber() {
  function flattenCuesForType(cues: Record<string, Cue[]>, cueTypeId: number): CueWithLineId[] {
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

  return { computeRenumber, flattenCuesForType };
}
