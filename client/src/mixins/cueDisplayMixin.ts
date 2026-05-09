import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import { contrastColor } from 'contrast-color';
import type { Cue, CueType } from '@/types/api/cues';
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
  },
});
