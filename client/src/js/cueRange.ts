/** Largest number of cues a single "Add Range" may create. */
export const MAX_RANGE_CUES = 10000;

/**
 * Expand a whole-number range into cue identifiers.
 *
 * Returns null unless both ends are whole numbers, `from` is no higher than `to`
 * and the range holds at most {@link MAX_RANGE_CUES} cues.
 */
export function expandWholeRange(from: string, to: string): string[] | null {
  const a = from.trim();
  const b = to.trim();
  if (!/^\d+$/.test(a) || !/^\d+$/.test(b)) return null;
  const start = Number.parseInt(a, 10);
  const end = Number.parseInt(b, 10);
  if (start > end || end - start >= MAX_RANGE_CUES) return null;
  return Array.from({ length: end - start + 1 }, (_, i) => String(start + i));
}

/** The live view's single-field range syntax: "5 > 10". */
export function parseRangeText(input: string): string[] | null {
  const match = /^(\d+)\s*>\s*(\d+)$/.exec(input.trim());
  if (!match) return null;
  return expandWholeRange(match[1], match[2]);
}
