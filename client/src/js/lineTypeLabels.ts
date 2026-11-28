import { LINE_TYPES, type LineType } from '@/constants/lineTypes';

/** Short display label for a line type, shared by every new Design E component. */
export const LINE_TYPE_LABELS: Record<LineType, string> = {
  [LINE_TYPES.DIALOGUE]: 'Dialogue',
  [LINE_TYPES.STAGE_DIRECTION]: 'Direction',
  [LINE_TYPES.CUE_LINE]: 'Cue',
  [LINE_TYPES.SPACING]: 'Gap',
};

// Widened (an assignment, not a cast) so an arbitrary `number` — `line_type` is a plain
// `number` on the API types — can index it and honestly yield `undefined` for a type
// this map doesn't know.
const LABELS_BY_NUMBER: Partial<Record<number, string>> = LINE_TYPE_LABELS;

export function lineTypeLabel(lineType: number): string {
  return LABELS_BY_NUMBER[lineType] ?? 'Line';
}
