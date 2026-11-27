import type { Cue, LinePosition } from '@/types/api/cues';

/**
 * Suggested cue numbers and "nearest cues", per HANDOFF section 2.5.
 *
 * All arithmetic is done on BigInt-scaled decimals, never floating point, so that
 * 13.1 + 0.2 and friends behave exactly.
 */

const NUMERIC = /^\d+(\.\d+)?$/;
const MAX_SUGGESTED_PLACES = 2;

export function isNumericIdent(value: string | null | undefined): value is string {
  return value != null && NUMERIC.test(value);
}

/** Strip leading zeros and trailing fractional zeros: "013.50" -> "13.5". */
export function canonicalDecimal(value: string): string {
  const [rawInt, rawFrac = ''] = value.split('.');
  const int = rawInt.replace(/^0+(?=\d)/, '');
  const frac = rawFrac.replace(/0+$/, '');
  return frac ? `${int}.${frac}` : int;
}

function decimalPlaces(value: string): number {
  const frac = canonicalDecimal(value).split('.')[1];
  return frac ? frac.length : 0;
}

function toScaled(value: string, places: number): bigint {
  const [int, frac = ''] = canonicalDecimal(value).split('.');
  return BigInt(int + frac.padEnd(places, '0'));
}

function fromScaled(value: bigint, places: number): string {
  const text = value.toString().padStart(places + 1, '0');
  const int = text.slice(0, text.length - places);
  const frac = text.slice(text.length - places);
  return canonicalDecimal(places > 0 ? `${int}.${frac}` : int);
}

export type SuggestionBlankReason = 'out-of-order' | 'no-free-number' | null;

export interface SuggestionResult {
  /** The suggested number, or null when none can be suggested. */
  value: string | null;
  /** Why it is blank, when it matters to the person. */
  reason: SuggestionBlankReason;
  /** The numeric neighbours the suggestion was based on (null when absent). */
  previous: string | null;
  next: string | null;
}

/**
 * Suggest the next cue number.
 *
 * @param before Idents of this type on or above the line, in script order.
 * @param after Idents of this type below the line, in script order.
 * @param used Every ident of this type in the revision.
 */
export function suggestCueNumber(
  before: readonly (string | null)[],
  after: readonly (string | null)[],
  used: Iterable<string | null>
): SuggestionResult {
  const previous = [...before].reverse().find(isNumericIdent) ?? null;
  const next = after.find(isNumericIdent) ?? null;
  const blank = (reason: SuggestionBlankReason): SuggestionResult => ({
    value: null,
    reason,
    previous,
    next,
  });
  const found = (value: string): SuggestionResult => ({
    value,
    reason: null,
    previous,
    next,
  });

  const places = Math.max(
    MAX_SUGGESTED_PLACES,
    previous ? decimalPlaces(previous) : 0,
    next ? decimalPlaces(next) : 0
  );
  const one = 10n ** BigInt(places);
  const usedSet = new Set<string>();
  for (const ident of used) {
    if (isNumericIdent(ident)) usedSet.add(canonicalDecimal(ident));
  }
  const isUsed = (v: bigint) => usedSet.has(fromScaled(v, places));

  const P = previous ? toScaled(previous, places) : null;
  const N = next ? toScaled(next, places) : null;

  // 1. Neither neighbour.
  if (P == null && N == null) {
    let w = one;
    while (isUsed(w)) w += one;
    return found(fromScaled(w, places));
  }

  // 2. Only a previous cue.
  if (P != null && N == null) {
    let w = (P / one + 1n) * one;
    while (isUsed(w)) w += one;
    return found(fromScaled(w, places));
  }

  // 3. Only a following cue.
  if (P == null && N != null) {
    if (N > one) {
      let w = ((N + one - 1n) / one) * one - one;
      while (isUsed(w) && w > one) w -= one;
      return isUsed(w) ? blank('no-free-number') : found(fromScaled(w, places));
    }
    if (N <= 0n || N % 2n !== 0n) return blank('no-free-number');
    const half = N / 2n;
    if (decimalPlaces(fromScaled(half, places)) > MAX_SUGGESTED_PLACES || isUsed(half)) {
      return blank('no-free-number');
    }
    return found(fromScaled(half, places));
  }

  // Both neighbours from here on.
  const p = P as bigint;
  const n = N as bigint;
  const prevText = previous as string;

  // 4. Numbers out of order.
  if (p >= n) return blank('out-of-order');

  // 5. The next whole number, if it fits and is free.
  const whole = (p / one + 1n) * one;
  if (whole < n && !isUsed(whole)) return found(fromScaled(whole, places));

  // 6. Add one unit of p's last place while below n.
  const prevPlaces = decimalPlaces(prevText);
  if (prevPlaces >= 1 && prevPlaces <= MAX_SUGGESTED_PLACES) {
    const unit = 10n ** BigInt(places - prevPlaces);
    for (let v = p + unit; v < n; v += unit) {
      if (!isUsed(v)) return found(fromScaled(v, places));
    }
  }

  // 7. Finer places, taking the free value nearest the midpoint (lower on a tie).
  const startPlaces = prevPlaces === 0 ? 1 : prevPlaces + 1;
  for (let k = startPlaces; k <= MAX_SUGGESTED_PLACES; k += 1) {
    const unit = 10n ** BigInt(places - k);
    const twoMid = p + n;
    // Largest grid value at or below the midpoint (2 * lower <= p + n).
    const lower = (twoMid / (2n * unit)) * unit;
    let upper = lower + unit;
    let down = lower;
    while ((down > p && down < n) || (upper > p && upper < n)) {
      const downOk = down > p && down < n;
      const upOk = upper > p && upper < n;
      if (downOk && (!upOk || twoMid - 2n * down <= 2n * upper - twoMid)) {
        if (!isUsed(down)) return found(fromScaled(down, places));
        down -= unit;
      } else if (upOk) {
        if (!isUsed(upper)) return found(fromScaled(upper, places));
        upper += unit;
      } else {
        break;
      }
    }
  }

  // 8. Nothing fits.
  return blank('no-free-number');
}

// ── Positions ────────────────────────────────────────────────────────────────

export interface PositionedCue {
  cue: Cue;
  page: number;
  index: number;
}

export interface LineKey {
  page: number;
  index: number;
}

function compareKeys(a: LineKey, b: LineKey): number {
  return a.page !== b.page ? a.page - b.page : a.index - b.index;
}

/**
 * Every cue of one type in script order, positioned from the server's
 * `line_positions` so that lines on pages that are not loaded still count.
 *
 * Cues whose line has no known position are left out: their position is unknown,
 * which must never be treated as "first line".
 */
export function orderedCuesOfType(
  cuesByLine: Record<string, Cue[]>,
  linePositions: Record<string, LinePosition>,
  cueTypeId: number
): PositionedCue[] {
  const entries: PositionedCue[] = [];
  for (const [lineId, cues] of Object.entries(cuesByLine)) {
    const position = linePositions[lineId];
    if (!position || position.page == null) continue;
    for (const cue of cues) {
      if (cue.cue_type_id === cueTypeId) {
        entries.push({ cue, page: position.page, index: position.index });
      }
    }
  }
  entries.sort(
    (a, b) =>
      compareKeys(a, b) ||
      (a.cue.line_position ?? 0) - (b.cue.line_position ?? 0) ||
      (a.cue.sort_order ?? 0) - (b.cue.sort_order ?? 0)
  );
  return entries;
}

/** Split ordered cues into those on or above the line and those below it. */
export function splitAtLine(
  ordered: readonly PositionedCue[],
  line: LineKey
): { before: PositionedCue[]; after: PositionedCue[] } {
  const before: PositionedCue[] = [];
  const after: PositionedCue[] = [];
  for (const entry of ordered) {
    (compareKeys(entry, line) <= 0 ? before : after).push(entry);
  }
  return { before, after };
}

export interface NearestCue {
  cue: Cue;
  /** "above", "this line" or "below" when on the current page, else the page. */
  where: string;
}

function describeWhere(entry: PositionedCue, line: LineKey, side: 'before' | 'after'): string {
  if (entry.page !== line.page) return `page ${entry.page}`;
  if (entry.index === line.index) return 'this line';
  return side === 'before' ? 'above' : 'below';
}

export function nearestCues(
  ordered: readonly PositionedCue[],
  line: LineKey
): { previous: NearestCue | null; next: NearestCue | null } {
  const { before, after } = splitAtLine(ordered, line);
  const prev = before[before.length - 1];
  const next = after[0];
  return {
    previous: prev ? { cue: prev.cue, where: describeWhere(prev, line, 'before') } : null,
    next: next ? { cue: next.cue, where: describeWhere(next, line, 'after') } : null,
  };
}
