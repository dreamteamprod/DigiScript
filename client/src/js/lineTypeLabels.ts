import { LINE_TYPES, type LineType } from '@/constants/lineTypes';

/** Short display label for a line type, shared by every new Design E component. */
export const LINE_TYPE_LABELS: Record<LineType, string> = {
  [LINE_TYPES.DIALOGUE]: 'Dialogue',
  [LINE_TYPES.STAGE_DIRECTION]: 'Direction',
  [LINE_TYPES.CUE_LINE]: 'Cue',
  [LINE_TYPES.SPACING]: 'Gap',
};

export function lineTypeLabel(lineType: number): string {
  return LINE_TYPE_LABELS[lineType as LineType] ?? 'Line';
}
