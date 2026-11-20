import {
  buildMruCharacterOptions,
  buildMruCharacterGroupOptions,
  type NamedItem,
  type SelectOption,
  type TmpScript,
} from './mruSortUtils';
import type { StageDirectionStyle } from '@/types/api/script';

/**
 * The character/character-group/stage-direction-style select options for a line part's
 * editor: most-recently-used first when the user has that setting on, else the plain
 * list. Mirrors the equivalent option-building still duplicated inline in the classic
 * `ScriptLinePart.vue` — keep both in sync if the MRU or option-building rules change.
 */
export function characterSelectOptions(
  characters: NamedItem[],
  tmpScript: TmpScript,
  useMru: boolean
): SelectOption[] {
  if (useMru) {
    const sorted = buildMruCharacterOptions(characters, tmpScript);
    if (sorted) return sorted;
  }
  return [{ value: null, text: 'N/A' }, ...characters.map((c) => ({ value: c.id, text: c.name }))];
}

export function characterGroupSelectOptions(
  characterGroups: NamedItem[],
  tmpScript: TmpScript,
  useMru: boolean
): SelectOption[] {
  if (useMru) {
    const sorted = buildMruCharacterGroupOptions(characterGroups, tmpScript);
    if (sorted) return sorted;
  }
  return [
    { value: null, text: 'N/A' },
    ...characterGroups.map((g) => ({ value: g.id, text: g.name })),
  ];
}

export function stageDirectionStyleSelectOptions(
  styles: StageDirectionStyle[] | undefined
): { value: number | null; text: string | null }[] {
  return [
    { value: null, text: 'N/A' },
    ...(styles ?? []).map((s) => ({ value: s.id, text: s.description })),
  ];
}
