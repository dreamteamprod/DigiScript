import { mapGetters } from 'vuex';

/**
 * Shared mixin for script navigation and filtering logic.
 * Provides utilities for navigating through script lines and determining visibility.
 */
export default {
  computed: {
    needsHeadings() {
      let { previousLine } = this;
      let lineIndex = this.previousLineIndex;
      while (previousLine != null && (previousLine.stage_direction === true
          || this.isWholeLineCut(previousLine))) {
        [lineIndex, previousLine] = this.getPreviousLineForIndex(previousLine.page, lineIndex);
      }

      const ret = [];
      this.line.line_parts.forEach(function checkLinePartNeedsHeading(part) {
        if (previousLine == null
          || previousLine.line_parts.length !== this.line.line_parts.length) {
          ret.push(true);
        } else if (previousLine.act_id !== this.line.act_id || previousLine.scene_id !== this.line.scene_id) {
          ret.push(true);
        } else {
          const matchingIndex = previousLine.line_parts.find((prevPart) => (
            prevPart.part_index === part.part_index));
          if (matchingIndex == null) {
            ret.push(true);
          } else {
            ret.push(!(matchingIndex.character_id === part.character_id
              && matchingIndex.character_group_id === part.character_group_id));
          }
        }
      }, this);
      return ret;
    },
    ...mapGetters(['GET_SCRIPT_PAGE', 'SCRIPT_CUTS']),
  },
  methods: {
    getPreviousLineForIndex(pageIndex, lineIndex) {
      if (lineIndex > 0) {
        return [lineIndex - 1, this.GET_SCRIPT_PAGE(pageIndex)[lineIndex - 1]];
      }
      let loopPageNo = pageIndex - 1;
      while (loopPageNo >= 1) {
        const loopPage = this.GET_SCRIPT_PAGE(loopPageNo);
        if (loopPage.length > 0) {
          return [loopPage.length - 1, loopPage[loopPage.length - 1]];
        }
        loopPageNo -= 1;
      }
      return [null, null];
    },
    isWholeLineCut(line) {
      return line.line_parts.every((linePart) => (this.SCRIPT_CUTS.includes(linePart.id)
          || linePart.line_text == null || linePart.line_text.trim().length === 0), this);
    },
  },
};
