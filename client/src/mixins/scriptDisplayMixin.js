import { mapGetters } from 'vuex';
import { LINE_TYPES } from '@/constants/lineTypes';
import { TEXT_ALIGNMENT_CSS } from '@/constants/textAlignment';

/**
 * Shared mixin for script display presentation logic.
 * Handles stage directions, act/scene labels, intervals, and viewport tracking.
 *
 * This mixin assumes the component has:
 * - Props: line, lineIndex, previousLine, acts, scenes,
 *          stageDirectionStyles, stageDirectionStyleOverrides
 * - Optional props: previousLineIndex (required for interval/cut-aware features)
 * - Optional refs: lineContainer (required for viewport tracking in live view)
 * - Optional methods: isWholeLineCut, getPreviousLineForIndex (from scriptNavigationMixin,
 *                     required for interval/cut-aware features)
 *
 * Components using only the alignment/styling features (headingStyle, dialogueStyle,
 * scriptTextAlign, stageDirectionStyling) do not need the optional dependencies.
 */
export default {
  data() {
    return {
      observer: null,
    };
  },
  computed: {
    needsActSceneLabel() {
      let { previousLine } = this;
      let lineIndex = this.previousLineIndex;
      while (previousLine != null && this.isWholeLineCut(previousLine)) {
        [lineIndex, previousLine] = this.getPreviousLineForIndex(previousLine.page, lineIndex);
      }
      if (previousLine == null) {
        return true;
      }
      return !(
        previousLine.act_id === this.line.act_id && previousLine.scene_id === this.line.scene_id
      );
    },
    needsIntervalBanner() {
      let { previousLine, lineIndex } = this;
      while (previousLine != null && this.isWholeLineCut(previousLine)) {
        [lineIndex, previousLine] = this.getPreviousLineForIndex(previousLine.page, lineIndex);
      }
      if (previousLine == null) {
        return false;
      }
      return previousLine.act_id !== this.line.act_id;
    },
    previousActLabel() {
      return this.acts.find((act) => act.id === this.previousLine.act_id).name;
    },
    actLabel() {
      return this.acts.find((act) => act.id === this.line.act_id).name;
    },
    sceneLabel() {
      return this.scenes.find((scene) => scene.id === this.line.scene_id).name;
    },
    stageDirectionStyle() {
      const sdStyle = this.stageDirectionStyles.find(
        (style) => style.id === this.line.stage_direction_style_id
      );
      const override = this.stageDirectionStyleOverrides.find(
        (elem) => elem.settings.id === sdStyle.id
      );
      if (this.line.line_type === LINE_TYPES.STAGE_DIRECTION) {
        return override ? override.settings : sdStyle;
      }
      return null;
    },
    stageDirectionStyling() {
      if (this.line.stage_direction_style_id == null || this.stageDirectionStyle == null) {
        return {
          'background-color': 'darkslateblue',
          'font-style': 'italic',
        };
      }
      const style = {
        'font-weight': this.stageDirectionStyle.bold ? 'bold' : 'normal',
        'font-style': this.stageDirectionStyle.italic ? 'italic' : 'normal',
        'text-decoration-line': this.stageDirectionStyle.underline ? 'underline' : 'none',
        color: this.stageDirectionStyle.text_colour,
      };
      if (this.stageDirectionStyle.enable_background_colour) {
        style['background-color'] = this.stageDirectionStyle.background_colour;
      }
      return style;
    },
    scriptTextAlign() {
      const alignment = this.USER_SETTINGS.script_text_alignment || 2;
      return TEXT_ALIGNMENT_CSS[alignment] || 'center';
    },
    headingStyle() {
      return { textAlign: this.scriptTextAlign };
    },
    dialogueStyle() {
      return { textAlign: this.scriptTextAlign };
    },
    needsHeadingsAny() {
      return this.needsHeadings.some((x) => x === true);
    },
    needsHeadingsAll() {
      return this.needsHeadings.every((x) => x === true);
    },
    ...mapGetters(['USER_SETTINGS']),
  },
  mounted() {
    // Only set up viewport observer if lineContainer ref exists
    // (e.g., live view needs this, but editor view does not)
    if (this.$refs.lineContainer) {
      this.observer = new MutationObserver((mutations) => {
        for (const m of mutations) {
          const newValue = m.target.getAttribute(m.attributeName);
          this.$nextTick(() => {
            this.onClassChange(newValue, m.oldValue);
          });
        }
      });

      this.observer.observe(this.$refs.lineContainer, {
        attributes: true,
        attributeOldValue: true,
        attributeFilter: ['class'],
      });
    }
  },
  destroyed() {
    if (this.observer) {
      this.observer.disconnect();
    }
  },
  methods: {
    onClassChange(classAttrValue, oldClassAttrValue) {
      const classList = classAttrValue.split(' ');
      const oldClassList = oldClassAttrValue.split(' ');
      if (
        classList.includes('last-script-element') &&
        !oldClassList.includes('last-script-element')
      ) {
        this.$emit('last-line-change', this.line.page, this.lineIndex);
      }
      if (
        classList.includes('first-script-element') &&
        !oldClassList.includes('first-script-element')
      ) {
        let previousLine = null;
        if (this.previousLine != null) {
          previousLine = `page_${this.previousLine.page}_line_${this.previousLineIndex}`;
        }
        this.$emit('first-line-change', this.line.page, this.lineIndex, previousLine);
      }
    },
    startInterval() {
      this.$emit('start-interval', this.acts.find((act) => act.id === this.previousLine.act_id).id);
    },
  },
};
