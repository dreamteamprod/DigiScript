import { computed, toValue, type MaybeRefOrGetter } from 'vue';
import { useScriptStore } from '@/stores/script';
import type { Cue, LinePosition } from '@/types/api/cues';
import type { ScriptLine } from '@/types/api/script';

/**
 * Suggested cue numbers, and the "nearest cues" shown beside them.
 *
 * A suggestion is for a new cue of one type on one line. It looks at the cues of that type on or
 * above the line (`before`), below it (`after`) and every number of that type in the revision
 * (`used`). Only plain numbers such as `13` or `13.5` count as neighbours; others, like `INTRO`,
 * are ignored. It prefers the next whole number when there is room, and otherwise a decimal
 * between the two neighbours; the numbered cases in `suggestCueNumber` spell out the rules.
 *
 * All arithmetic is done on BigInt-scaled decimals, never floating point, so that
 * 13.1 + 0.2 and friends behave exactly.
 */

const NUMERIC = /^\d+(\.\d+)?$/;
const MAX_SUGGESTED_PLACES = 2;

export function isNumericIdent(value: string | null | undefined): value is string {
  return value != null && NUMERIC.test(value);
}

function trimTrailingZeros(text: string): string {
  let end = text.length;
  while (end > 0 && text.charCodeAt(end - 1) === 48) end -= 1;
  return text.slice(0, end);
}

/** Strip leading zeros and trailing fractional zeros: "013.50" -> "13.5". */
export function canonicalDecimal(value: string): string {
  const [rawInt, rawFrac = ''] = value.split('.');
  const int = rawInt.replace(/^0+(?=\d)/, '');
  const frac = trimTrailingZeros(rawFrac);
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

/** The numbers around a suggestion, scaled so that every value is a whole BigInt. */
interface Grid {
  places: number;
  /** One whole unit (1.00) on this grid. */
  one: bigint;
  isUsed: (value: bigint) => boolean;
}

/** The first whole number at or after `from` that is not already used. */
function firstFreeWhole(grid: Grid, from: bigint): bigint {
  let whole = from;
  while (grid.isUsed(whole)) whole += grid.one;
  return whole;
}

/** The next whole number above `value`. */
function wholeAbove(grid: Grid, value: bigint): bigint {
  return (value / grid.one + 1n) * grid.one;
}

/** Rules 1 to 3: at most one neighbour. */
function withoutBothNeighbours(grid: Grid, p: bigint | null, n: bigint | null): bigint | null {
  if (n == null) return firstFreeWhole(grid, p == null ? grid.one : wholeAbove(grid, p));

  // Only a following cue: the whole number below it, stepping down past used ones...
  if (n > grid.one) {
    let whole = ((n + grid.one - 1n) / grid.one) * grid.one - grid.one;
    while (grid.isUsed(whole) && whole > grid.one) whole -= grid.one;
    return grid.isUsed(whole) ? null : whole;
  }
  // ...or half of it when it is 1 or less, if that needs no more than two decimals.
  if (n <= 0n || n % 2n !== 0n) return null;
  const half = n / 2n;
  const tooFine = decimalPlaces(fromScaled(half, grid.places)) > MAX_SUGGESTED_PLACES;
  return tooFine || grid.isUsed(half) ? null : half;
}

/** Rule 6: add one unit of p's last place, repeatedly, while below n. */
function stepFromPrevious(grid: Grid, p: bigint, n: bigint, prevPlaces: number): bigint | null {
  if (prevPlaces < 1 || prevPlaces > MAX_SUGGESTED_PLACES) return null;
  const unit = 10n ** BigInt(grid.places - prevPlaces);
  for (let value = p + unit; value < n; value += unit) {
    if (!grid.isUsed(value)) return value;
  }
  return null;
}

/** Rule 7 at one precision: the free value nearest the midpoint of p and n (the lower on a tie). */
function nearestMidpoint(grid: Grid, p: bigint, n: bigint, places: number): bigint | null {
  const unit = 10n ** BigInt(grid.places - places);
  const twoMid = p + n;
  // The largest value on this grid at or below the midpoint (2 * lower <= p + n).
  let down = (twoMid / (2n * unit)) * unit;
  let up = down + unit;
  const inRange = (value: bigint) => value > p && value < n;
  while (inRange(down) || inRange(up)) {
    const pickDown = inRange(down) && (!inRange(up) || twoMid - 2n * down <= 2n * up - twoMid);
    const candidate = pickDown ? down : up;
    if (!grid.isUsed(candidate)) return candidate;
    if (pickDown) down -= unit;
    else up += unit;
  }
  return null;
}

/** Rule 7: finer and finer places, up to two decimals, until one has a free value. */
function finerBetween(grid: Grid, p: bigint, n: bigint, prevPlaces: number): bigint | null {
  const start = prevPlaces === 0 ? 1 : prevPlaces + 1;
  for (let places = start; places <= MAX_SUGGESTED_PLACES; places += 1) {
    const found = nearestMidpoint(grid, p, n, places);
    if (found != null) return found;
  }
  return null;
}

/** Rules 5 to 7: room between a previous and a following number (p < n). */
function between(grid: Grid, p: bigint, n: bigint, prevPlaces: number): bigint | null {
  const whole = wholeAbove(grid, p);
  if (whole < n && !grid.isUsed(whole)) return whole;
  return stepFromPrevious(grid, p, n, prevPlaces) ?? finerBetween(grid, p, n, prevPlaces);
}

function makeGrid(
  previous: string | null,
  next: string | null,
  used: Iterable<string | null>
): Grid {
  const places = Math.max(
    MAX_SUGGESTED_PLACES,
    previous ? decimalPlaces(previous) : 0,
    next ? decimalPlaces(next) : 0
  );
  const usedSet = new Set<string>();
  for (const ident of used) {
    if (isNumericIdent(ident)) usedSet.add(canonicalDecimal(ident));
  }
  return {
    places,
    one: 10n ** BigInt(places),
    isUsed: (value) => usedSet.has(fromScaled(value, places)),
  };
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
  const grid = makeGrid(previous, next, used);
  const result = (
    value: bigint | null,
    reason: SuggestionBlankReason = 'no-free-number'
  ): SuggestionResult => ({
    value: value == null ? null : fromScaled(value, grid.places),
    reason: value == null ? reason : null,
    previous,
    next,
  });

  const p = previous ? toScaled(previous, grid.places) : null;
  const n = next ? toScaled(next, grid.places) : null;
  if (p == null || n == null) return result(withoutBothNeighbours(grid, p, n));
  // Numbers out of order: nothing sensible to suggest.
  if (p >= n) return result(null, 'out-of-order');
  return result(between(grid, p, n, decimalPlaces(previous as string)));
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
    if (position?.page == null) continue;
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
  const prev = before.at(-1);
  const next = after[0];
  return {
    previous: prev ? { cue: prev.cue, where: describeWhere(prev, line, 'before') } : null,
    next: next ? { cue: next.cue, where: describeWhere(next, line, 'after') } : null,
  };
}

// ── Wiring to the stores ─────────────────────────────────────────────────────

/**
 * The suggested number and nearest cues for adding a cue of one type to a line.
 *
 * The line's own position comes from the loaded page; the cues around it come from
 * the server's `line_positions`, so neighbours on pages that are not loaded count.
 */
export function useLineSuggestion(
  line: MaybeRefOrGetter<ScriptLine>,
  typeId: MaybeRefOrGetter<number | null>
) {
  const scriptStore = useScriptStore();

  const lineKey = computed<LineKey | null>(() => {
    const current = toValue(line);
    if (current.page == null) return null;
    const index = scriptStore.getScriptPage(current.page).findIndex((l) => l.id === current.id);
    return index >= 0 ? { page: current.page, index } : null;
  });

  const ordered = computed(() => {
    const id = toValue(typeId);
    return id == null ? [] : orderedCuesOfType(scriptStore.cues, scriptStore.linePositions, id);
  });

  const nearest = computed(() =>
    lineKey.value ? nearestCues(ordered.value, lineKey.value) : { previous: null, next: null }
  );

  const suggestion = computed<SuggestionResult>(() => {
    const id = toValue(typeId);
    if (id == null || lineKey.value == null) {
      return { value: null, reason: null, previous: null, next: null };
    }
    const { before, after } = splitAtLine(ordered.value, lineKey.value);
    // Every cue of the type counts as used, including those whose line has no known position.
    const used = Object.values(scriptStore.cues)
      .flat()
      .filter((c) => c.cue_type_id === id)
      .map((c) => c.ident);
    return suggestCueNumber(
      before.map((e) => e.cue.ident),
      after.map((e) => e.cue.ident),
      used
    );
  });

  return { lineKey, nearest, suggestion };
}
