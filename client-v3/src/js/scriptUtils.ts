import { LINE_TYPES } from '@/constants/lineTypes';
import type { ScriptLine } from '@/types/api/script';

export function isWholeLineCut(line: ScriptLine, cuts: (number | null)[]): boolean {
  if (line.line_type === LINE_TYPES.CUE_LINE) {
    return false;
  }

  if (line.line_type === LINE_TYPES.SPACING) {
    return true;
  }

  return line.line_parts.every(
    (linePart) =>
      cuts.includes(linePart.id) ||
      linePart.line_text == null ||
      linePart.line_text.trim().length === 0
  );
}

export default { isWholeLineCut };
