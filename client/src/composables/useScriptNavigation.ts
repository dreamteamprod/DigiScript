import { LINE_TYPES } from '@/constants/lineTypes';
import { isWholeLineCut } from '@/js/scriptUtils';
import type { ScriptLine } from '@/types/api/script';

function checkIsUntaggedStageDirection(line: ScriptLine): boolean {
  return (
    line.line_type === LINE_TYPES.STAGE_DIRECTION &&
    line.line_parts[0]?.character_id == null &&
    line.line_parts[0]?.character_group_id == null
  );
}

export function getPreviousLineAcrossPages(
  current: ScriptLine,
  getPage: (page: number) => ScriptLine[]
): ScriptLine | null {
  const page = getPage(current.page ?? 0);
  const idx = page.indexOf(current);
  if (idx > 0) return page[idx - 1];
  let loopPageNo = (current.page ?? 0) - 1;
  while (loopPageNo >= 1) {
    const loopPage = getPage(loopPageNo);
    if (loopPage.length > 0) return loopPage[loopPage.length - 1];
    loopPageNo -= 1;
  }
  return null;
}

function needsActSceneLabel(
  line: ScriptLine,
  previousLine: ScriptLine | null,
  cuts: (number | null)[],
  getPage: (page: number) => ScriptLine[]
): boolean {
  let prev: ScriptLine | null = previousLine;
  while (prev != null && isWholeLineCut(prev, cuts)) {
    prev = getPreviousLineAcrossPages(prev, getPage);
  }
  if (prev == null) return true;
  return !(prev.act_id === line.act_id && prev.scene_id === line.scene_id);
}

export function useScriptNavigation() {
  function needsHeadings(
    line: ScriptLine,
    previousLine: ScriptLine | null,
    cuts: (number | null)[],
    getPage: (page: number) => ScriptLine[]
  ): boolean[] {
    let prev: ScriptLine | null = previousLine;
    while (prev != null && (checkIsUntaggedStageDirection(prev) || isWholeLineCut(prev, cuts))) {
      prev = getPreviousLineAcrossPages(prev, getPage);
    }

    return line.line_parts.map((part) => {
      if (prev?.line_parts.length !== line.line_parts.length) return true;
      if (prev.act_id !== line.act_id || prev.scene_id !== line.scene_id) return true;
      const match = prev.line_parts.find((p) => p.part_index === part.part_index);
      if (!match) return true;
      return !(
        match.character_id === part.character_id &&
        match.character_group_id === part.character_group_id
      );
    });
  }

  return { needsHeadings, needsActSceneLabel, checkIsUntaggedStageDirection };
}
