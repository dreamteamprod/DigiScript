import { contrastColor } from '@/js/utils';
import { useShowStore } from '@/stores/show';
import { useUserStore } from '@/stores/user';
import type { Cue, CueGroup } from '@/types/api/cues';

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

  function cueGroupLabel(group: CueGroup, cues: Cue[]): string {
    const cueType = showStore.cueTypeById(group.cue_type_id);
    const prefix = cueType?.prefix ?? '';
    if (group.label_override) return `${prefix} - ${group.label_override}`;
    if (cues.length === 0) return prefix;
    const first = cues[0].ident ?? '';
    const last = cues[cues.length - 1].ident ?? '';
    if (first === last) return `${prefix} ${first}`;
    return `${prefix} ${first} - ${prefix} ${last}`;
  }

  function cueGroupBackgroundColour(group: CueGroup): string {
    const cueType = showStore.cueTypeById(group.cue_type_id);
    if (!cueType) return '#000000';
    const override = userStore.cueColourOverrides.find((o) => o.cue_type_id === cueType.id);
    if (override?.colour) return override.colour;
    return cueType.colour ?? '#000000';
  }

  function cueGroupPrefix(group: CueGroup): string {
    return showStore.cueTypeById(group.cue_type_id)?.prefix ?? '';
  }

  function cueGroupIdentLabel(group: CueGroup, cues: Cue[]): string {
    if (group.label_override) return `- ${group.label_override}`;
    if (cues.length === 0) return '';
    const first = cues[0].ident ?? '';
    const last = cues[cues.length - 1].ident ?? '';
    if (first === last) return first;
    const prefix = showStore.cueTypeById(group.cue_type_id)?.prefix ?? '';
    return `${first} - ${prefix} ${last}`;
  }

  return {
    cuePrefix,
    cueLabel,
    cueBackgroundColour,
    cueGroupLabel,
    cueGroupBackgroundColour,
    cueGroupPrefix,
    cueGroupIdentLabel,
    contrastColor,
  };
}
