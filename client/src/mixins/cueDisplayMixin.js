import { mapGetters } from 'vuex';
import { contrastColor } from 'contrast-color';

/**
 * Shared mixin for cue display logic across live view components.
 * Provides methods for cue color handling with user override support.
 */
export default {
  computed: {
    ...mapGetters(['CUE_COLOUR_OVERRIDES']),
  },
  methods: {
    contrastColor,
    cuePrefix(cue) {
      const cueType = this.cueTypes.find((cT) => (cT.id === cue.cue_type_id));
      return cueType.prefix;
    },
    cueLabel(cue) {
      const cueType = this.cueTypes.find((cT) => cT.id === cue.cue_type_id);
      return `${cueType.prefix} ${cue.ident}`;
    },
    cueBackgroundColour(cue) {
      const cueType = this.cueTypes.find((ct) => ct.id === cue.cue_type_id);
      if (!cueType) return '#000000'; // Fallback

      // Check if user has an override for this cue type
      const override = this.CUE_COLOUR_OVERRIDES.find((o) => o.settings.id === cueType.id);
      if (override) {
        return override.settings.colour;
      }

      return cueType.colour;
    },
  },
};
