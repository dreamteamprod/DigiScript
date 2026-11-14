/**
 * Text alignment enum constants matching backend TextAlignment IntEnum
 */
export const TEXT_ALIGNMENT = {
  LEFT: 1,
  CENTER: 2,
  RIGHT: 3,
} as const;

export type TextAlignment = (typeof TEXT_ALIGNMENT)[keyof typeof TEXT_ALIGNMENT];

export const TEXT_ALIGNMENT_CSS: Record<TextAlignment, string> = {
  [TEXT_ALIGNMENT.LEFT]: 'left',
  [TEXT_ALIGNMENT.CENTER]: 'center',
  [TEXT_ALIGNMENT.RIGHT]: 'right',
};
