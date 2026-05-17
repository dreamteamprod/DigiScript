import { contrastColor } from 'contrast-color';
import { useShowStore } from '@/stores/show';
import { useUserStore } from '@/stores/user';
import type { Cue } from '@/types/api/cues';

export function useCueDisplay() {
  const showStore = useShowStore();
  const userStore = useUserStore();

  function cuePrefix(cue: Cue): string | null {
    return showStore.cueTypeById(cue.cue_type_id)?.prefix ?? null;
  }

  function cueLabel(cue: Cue): string {
    const prefix = cuePrefix(cue);
    return prefix ? `${prefix} ${cue.ident}` : (cue.ident ?? '');
  }

  function cueBackgroundColour(cue: Cue): string {
    const cueType = showStore.cueTypeById(cue.cue_type_id);
    if (!cueType) return '#000000';
    const override = userStore.cueColourOverrides.find((o) => o.cue_type_id === cueType.id);
    if (override?.colour) return override.colour;
    return cueType.colour ?? '#000000';
  }

  return { cuePrefix, cueLabel, cueBackgroundColour, contrastColor };
}
