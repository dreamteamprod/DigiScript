import { LINE_TYPES } from '@/constants/lineTypes';

/**
 * Determines if a script line is completely cut (all parts cut or empty).
 *
 * @param {Object} line - The script line object
 * @param {Array} cuts - Array of cut line part IDs
 * @returns {boolean} - True if the entire line is cut, false otherwise
 */
export function isWholeLineCut(line, cuts) {
  // CUE_LINE can never be completely cut
  if (line.line_type === LINE_TYPES.CUE_LINE) {
    return false;
  }

  // SPACING lines are always considered cut
  if (line.line_type === LINE_TYPES.SPACING) {
    return true;
  }

  // For other line types, check if all line parts are cut or empty
  return line.line_parts.every(
    (linePart) =>
      cuts.includes(linePart.id) ||
      linePart.line_text == null ||
      linePart.line_text.trim().length === 0
  );
}

export default { isWholeLineCut };
