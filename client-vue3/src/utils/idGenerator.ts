/**
 * Simple ID generator utility for form field accessibility
 */

let idCounter = 0;

/**
 * Generate a unique ID with optional prefix
 * @param prefix Optional prefix for the ID (default: 'id')
 * @returns Unique string ID
 */
export function generateId(prefix = 'id'): string {
  idCounter += 1;
  return `${prefix}-${idCounter}`;
}

/**
 * Reset the ID counter (useful for testing)
 */
export function resetIdCounter(): void {
  idCounter = 0;
}
