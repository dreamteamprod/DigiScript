/**
 * Text alignment enum constants matching backend TextAlignment IntEnum
 */
export const TEXT_ALIGNMENT = {
  LEFT: 1,
  CENTER: 2,
  RIGHT: 3,
};

/**
 * Map TEXT_ALIGNMENT enum values to CSS text-align values
 */
export const TEXT_ALIGNMENT_CSS = {
  [TEXT_ALIGNMENT.LEFT]: 'left',
  [TEXT_ALIGNMENT.CENTER]: 'center',
  [TEXT_ALIGNMENT.RIGHT]: 'right',
};