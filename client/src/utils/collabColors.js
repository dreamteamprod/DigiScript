/**
 * Generate a deterministic, visually distinct colour for a collaborator.
 * Uses HSL with fixed saturation/lightness, hashing userId to a hue.
 */
export function collabColor(userId) {
  const hue = (userId * 137.508) % 360; // golden-angle spacing
  return `hsl(${Math.round(hue)}, 65%, 45%)`;
}
