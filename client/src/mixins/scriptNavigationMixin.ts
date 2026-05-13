import { defineComponent } from 'vue';
import { mapGetters } from 'vuex';
import { LINE_TYPES } from '@/constants/lineTypes';
import { isWholeLineCut as isWholeLineCutUtil } from '@/js/scriptUtils';
import type { ScriptLine, ScriptLinePart } from '@/types/api/script';

export default defineComponent({
  computed: {
    needsHeadings(): boolean[] {
      let previousLine: ScriptLine | null = (this as any).previousLine;
      let lineIndex: number | null = (this as any).previousLineIndex;
      while (
        previousLine != null &&
        (previousLine.line_type === LINE_TYPES.STAGE_DIRECTION || this.isWholeLineCut(previousLine))
      ) {
        [lineIndex, previousLine] = this.getPreviousLineForIndex(previousLine.page, lineIndex!);
      }

      const line: ScriptLine = (this as any).line;
      const ret: boolean[] = [];
      line.line_parts.forEach(function checkLinePartNeedsHeading(this: any, part: ScriptLinePart) {
        if (previousLine == null || previousLine.line_parts.length !== line.line_parts.length) {
          ret.push(true);
        } else if (previousLine.act_id !== line.act_id || previousLine.scene_id !== line.scene_id) {
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
    getPreviousLineForIndex(
      pageIndex: number,
      lineIndex: number
    ): [number | null, ScriptLine | null] {
      if (lineIndex > 0) {
        return [lineIndex - 1, (this as any).GET_SCRIPT_PAGE(pageIndex)[lineIndex - 1]];
      }
      let loopPageNo = pageIndex - 1;
      while (loopPageNo >= 1) {
        const loopPage: ScriptLine[] = (this as any).GET_SCRIPT_PAGE(loopPageNo);
        if (loopPage.length > 0) {
          return [loopPage.length - 1, loopPage[loopPage.length - 1]];
        }
        loopPageNo -= 1;
      }
      return [null, null];
    },
    isWholeLineCut(line: ScriptLine): boolean {
      return isWholeLineCutUtil(line, (this as any).SCRIPT_CUTS);
    },
  },
});
