type NamedItem = { id: number; name: string };
type LinePart = { character_id?: number | null; character_group_id?: number | null };
type ScriptLine = { line_parts?: LinePart[] };
type TmpScript = Record<string, ScriptLine[]>;
export type SelectOption = { value: number | null; text: string };
export type CombinedSelectOption =
  | { value: null; text: string }
  | { label: string; options: { value: string; text: string }[] };

function countOccurrences(
  tmpScript: TmpScript,
  field: 'character_id' | 'character_group_id'
): Record<number, number> {
  const counts: Record<number, number> = {};
  Object.values(tmpScript).forEach((page) => {
    page.forEach((line) => {
      (line.line_parts ?? []).forEach((part) => {
        const id = part[field];
        if (id != null) {
          counts[id] = (counts[id] || 0) + 1;
        }
      });
    });
  });
  return counts;
}

/**
 * Returns character options sorted by frequency across the loaded script pages,
 * or null if no character data is present in tmpScript (caller should use default order).
 */
export function buildMruCharacterOptions(
  characters: NamedItem[],
  tmpScript: TmpScript
): SelectOption[] | null {
  const counts = countOccurrences(tmpScript, 'character_id');
  if (Object.keys(counts).length === 0) return null;
  const sorted = [...characters].sort((a, b) => (counts[b.id] || 0) - (counts[a.id] || 0));
  return [{ value: null, text: 'N/A' }, ...sorted.map((c) => ({ value: c.id, text: c.name }))];
}

/**
 * Returns character group options sorted by frequency across the loaded script pages,
 * or null if no group data is present in tmpScript (caller should use default order).
 */
export function buildMruCharacterGroupOptions(
  characterGroups: NamedItem[],
  tmpScript: TmpScript
): SelectOption[] | null {
  const counts = countOccurrences(tmpScript, 'character_group_id');
  if (Object.keys(counts).length === 0) return null;
  const sorted = [...characterGroups].sort((a, b) => (counts[b.id] || 0) - (counts[a.id] || 0));
  return [{ value: null, text: 'N/A' }, ...sorted.map((g) => ({ value: g.id, text: g.name }))];
}

/**
 * Builds a grouped options list for a combined character + character group dropdown.
 * Each section is independently sorted by MRU frequency when useMru is true and
 * frequency data is available; otherwise original order is preserved.
 * Option values use "c:<id>" for characters and "g:<id>" for groups.
 */
export function buildCombinedCharacterOptions(
  characters: NamedItem[],
  characterGroups: NamedItem[],
  tmpScript: TmpScript,
  useMru: boolean
): CombinedSelectOption[] {
  let sortedChars = [...characters];
  let sortedGroups = [...characterGroups];

  if (useMru) {
    const charCounts = countOccurrences(tmpScript, 'character_id');
    if (Object.keys(charCounts).length > 0) {
      sortedChars = [...characters].sort(
        (a, b) => (charCounts[b.id] || 0) - (charCounts[a.id] || 0)
      );
    }
    const groupCounts = countOccurrences(tmpScript, 'character_group_id');
    if (Object.keys(groupCounts).length > 0) {
      sortedGroups = [...characterGroups].sort(
        (a, b) => (groupCounts[b.id] || 0) - (groupCounts[a.id] || 0)
      );
    }
  }

  const result: CombinedSelectOption[] = [{ value: null, text: 'N/A' }];
  if (sortedChars.length > 0) {
    result.push({
      label: 'Characters',
      options: sortedChars.map((c) => ({ value: `c:${c.id}`, text: c.name })),
    });
  }
  if (sortedGroups.length > 0) {
    result.push({
      label: 'Character Groups',
      options: sortedGroups.map((g) => ({ value: `g:${g.id}`, text: g.name })),
    });
  }
  return result;
}
