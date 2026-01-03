/**
 * Script Line Type Constants
 *
 * These constants match the ScriptLineType enum values from the backend
 * (models/script.py). Use these instead of magic numbers throughout the codebase.
 */

export const LINE_TYPES = {
  DIALOGUE: 1,
  STAGE_DIRECTION: 2,
  CUE_LINE: 3,
  SPACING: 4,
};

export default LINE_TYPES;
