import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import { contrastColor } from 'contrast-color';
import type { Cue, CueGroup, CueType } from '@/types/api/cues';
import type { CueColourOverride } from '@/types/api/user';

export default defineComponent({
  computed: {
    ...mapGetters(['CUE_COLOUR_OVERRIDES']),
  },
  methods: {
    contrastColor,
    cuePrefix(cue: Cue): string | null {
      const cueType: CueType | undefined = (this as any).cueTypes?.find(
        (cT: CueType) => cT.id === cue.cue_type_id
      );
      return cueType?.prefix ?? null;
    },
    cueLabel(cue: Cue): string {
      const cueType: CueType | undefined = (this as any).cueTypes?.find(
        (cT: CueType) => cT.id === cue.cue_type_id
      );
      return `${cueType?.prefix} ${cue.ident}`;
    },
    cueBackgroundColour(cue: Cue): string {
      const cueType: CueType | undefined = (this as any).cueTypes?.find(
        (ct: CueType) => ct.id === cue.cue_type_id
      );
      if (!cueType) return '#000000';
      const override: CueColourOverride | undefined = this.CUE_COLOUR_OVERRIDES?.find(
        (o: any) => o.settings?.id === cueType.id
      );
      if (override) return (override as any).settings.colour;
      return cueType.colour ?? '#000000';
    },
    cueGroupLabel(group: CueGroup, cues: Cue[]): string {
      const cueType: CueType | undefined = (this as any).cueTypes?.find(
        (cT: CueType) => cT.id === group.cue_type_id
      );
      const prefix = cueType?.prefix ?? '';
      if (group.label_override) return `${prefix} - ${group.label_override}`;
      if (cues.length === 0) return prefix;
      const first = cues[0].ident ?? '';
      const last = cues[cues.length - 1].ident ?? '';
      if (first === last) return `${prefix} ${first}`;
      return `${prefix} ${first} - ${prefix} ${last}`;
    },
    cueGroupBackgroundColour(group: CueGroup): string {
      const cueType: CueType | undefined = (this as any).cueTypes?.find(
        (ct: CueType) => ct.id === group.cue_type_id
      );
      if (!cueType) return '#000000';
      const override: CueColourOverride | undefined = this.CUE_COLOUR_OVERRIDES?.find(
        (o: any) => o.settings?.id === cueType.id
      );
      if (override) return (override as any).settings.colour;
      return cueType.colour ?? '#000000';
    },
    cueGroupPrefix(group: CueGroup): string {
      const cueType: CueType | undefined = (this as any).cueTypes?.find(
        (ct: CueType) => ct.id === group.cue_type_id
      );
      return cueType?.prefix ?? '';
    },
    cueGroupIdentLabel(group: CueGroup, cues: Cue[]): string {
      const cueType: CueType | undefined = (this as any).cueTypes?.find(
        (ct: CueType) => ct.id === group.cue_type_id
      );
      if (group.label_override) return `- ${group.label_override}`;
      if (cues.length === 0) return '';
      const first = cues[0].ident ?? '';
      const last = cues[cues.length - 1].ident ?? '';
      if (first === last) return first;
      const prefix = cueType?.prefix ?? '';
      return `${first} - ${prefix} ${last}`;
    },
  },
});
