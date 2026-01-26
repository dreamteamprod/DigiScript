import { mapGetters } from 'vuex';
import { LINE_TYPES } from '@/constants/lineTypes';
import { isWholeLineCut as isWholeLineCutUtil } from '@/js/scriptUtils';

/**
 * Shared mixin for script navigation and filtering logic.
 * Provides utilities for navigating through script lines and determining visibility.
 */
export default {
  computed: {
    /**
     * Check if the current line is a tagged stage direction (has character/group).
     */
    isTaggedStageDirection() {
      if (this.line.line_type !== LINE_TYPES.STAGE_DIRECTION) {
        return false;
      }
      if (this.line.line_parts.length === 0) {
        return false;
      }
      const part = this.line.line_parts[0];
      return part.character_id != null || part.character_group_id != null;
    },
    needsHeadings() {
      let { previousLine } = this;
      let lineIndex = this.previousLineIndex;
      // Skip over untagged stage directions and cut lines
      // Tagged stage directions (with character/group) participate in heading logic
      while (
        previousLine != null &&
        (this.checkIsUntaggedStageDirection(previousLine) || this.isWholeLineCut(previousLine))
      ) {
        [lineIndex, previousLine] = this.getPreviousLineForIndex(previousLine.page, lineIndex);
      }

      const ret = [];
      this.line.line_parts.forEach(function checkLinePartNeedsHeading(part) {
        if (
          previousLine == null ||
          previousLine.line_parts.length !== this.line.line_parts.length
        ) {
          ret.push(true);
        } else if (
          previousLine.act_id !== this.line.act_id ||
          previousLine.scene_id !== this.line.scene_id
        ) {
          ret.push(true);
        } else {
          const matchingIndex = previousLine.line_parts.find(
            (prevPart) => prevPart.part_index === part.part_index
          );
          if (matchingIndex == null) {
            ret.push(true);
          } else {
            ret.push(
              !(
                matchingIndex.character_id === part.character_id &&
                matchingIndex.character_group_id === part.character_group_id
              )
            );
          }
        }
      }, this);
      return ret;
    },
    ...mapGetters(['GET_SCRIPT_PAGE', 'SCRIPT_CUTS']),
  },
  methods: {
    /**
     * Check if a line is an untagged stage direction (no character/group).
     * Untagged stage directions are skipped when determining character headings.
     */
    checkIsUntaggedStageDirection(line) {
      if (line.line_type !== LINE_TYPES.STAGE_DIRECTION) {
        return false;
      }
      if (line.line_parts.length === 0) {
        return true; // No parts means untagged
      }
      const part = line.line_parts[0];
      return part.character_id == null && part.character_group_id == null;
    },
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
      return isWholeLineCutUtil(line, this.SCRIPT_CUTS);
    },
  },
};
