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

function needsActSceneLabel(
  line: ScriptLine,
  previousLine: ScriptLine | null,
  cuts: (number | null)[],
  getPage: (page: number) => ScriptLine[]
): boolean {
  let prev: ScriptLine | null = previousLine;
  while (prev != null && isWholeLineCut(prev, cuts)) {
    const prevPage = getPage(prev.page ?? 0);
    const idx = prevPage.indexOf(prev);
    prev = idx > 0 ? prevPage[idx - 1] : null;
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
      const prevPage = getPage(prev.page ?? 0);
      const idx = prevPage.indexOf(prev);
      prev = idx > 0 ? prevPage[idx - 1] : null;
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
