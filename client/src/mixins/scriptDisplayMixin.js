/**
 * Shared mixin for script display presentation logic.
 * Handles stage directions, act/scene labels, intervals, and viewport tracking.
 *
 * This mixin assumes the component has:
 * - Props: line, lineIndex, previousLine, previousLineIndex, acts, scenes,
 *          stageDirectionStyles, stageDirectionStyleOverrides
 * - Refs: lineContainer
 * - Methods: isWholeLineCut, getPreviousLineForIndex (from scriptNavigationMixin)
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
      return !(previousLine.act_id === this.line.act_id
        && previousLine.scene_id === this.line.scene_id);
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
      return this.acts.find((act) => (act.id === this.previousLine.act_id)).name;
    },
    actLabel() {
      return this.acts.find((act) => (act.id === this.line.act_id)).name;
    },
    sceneLabel() {
      return this.scenes.find((scene) => (scene.id === this.line.scene_id)).name;
    },
    stageDirectionStyle() {
      const sdStyle = this.stageDirectionStyles.find(
        (style) => (style.id === this.line.stage_direction_style_id),
      );
      const override = this.stageDirectionStyleOverrides
        .find((elem) => elem.settings.id === sdStyle.id);
      if (this.line.line_type === 2) {
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
  },
  mounted() {
    /* eslint-disable no-restricted-syntax */
    this.observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        const newValue = m.target.getAttribute(m.attributeName);
        this.$nextTick(() => {
          this.onClassChange(newValue, m.oldValue);
        });
      }
    });
    /* eslint-enable no-restricted-syntax */

    this.observer.observe(this.$refs.lineContainer, {
      attributes: true,
      attributeOldValue: true,
      attributeFilter: ['class'],
    });
  },
  destroyed() {
    this.observer.disconnect();
  },
  methods: {
    onClassChange(classAttrValue, oldClassAttrValue) {
      const classList = classAttrValue.split(' ');
      const oldClassList = oldClassAttrValue.split(' ');
      if (classList.includes('last-script-element') && !oldClassList.includes('last-script-element')) {
        this.$emit('last-line-change', this.line.page, this.lineIndex);
      }
      if (classList.includes('first-script-element') && !oldClassList.includes('first-script-element')) {
        let previousLine = null;
        if (this.previousLine != null) {
          previousLine = `page_${this.previousLine.page}_line_${this.previousLineIndex}`;
        }
        this.$emit('first-line-change', this.line.page, this.lineIndex, previousLine);
      }
    },
    startInterval() {
      this.$emit('start-interval', this.acts.find((act) => (act.id === this.previousLine.act_id)).id);
    },
  },
};
