import { z } from 'zod';
import type { RawSetting } from '@/stores/settings';

/**
 * Creates a dynamic Zod schema based on raw settings configuration
 * This allows for flexible validation based on the actual settings structure from the server
 */
export function createSystemSettingsSchema(rawSettings: Record<string, RawSetting>) {
  const schemaFields: Record<string, z.ZodTypeAny> = {};

  Object.entries(rawSettings).forEach(([key, setting]) => {
    switch (setting.type) {
      case 'str':
        schemaFields[key] = z
          .string()
          .min(1, `${setting.display_name || key} is required`)
          .trim();
        break;

      case 'int':
        schemaFields[key] = z
          .union([z.string(), z.number()])
          .transform((val) => {
            const num = typeof val === 'string' ? parseInt(val, 10) : val;
            return Number.isNaN(num) ? val : num;
          })
          .pipe(
            z.number({
              message: `${setting.display_name || key} must be a valid number`,
            }),
          );
        break;

      case 'bool':
        schemaFields[key] = z.boolean();
        break;

      default:
        // For unknown types, allow any value but require it to exist
        schemaFields[key] = z.unknown();
        break;
    }
  });

  return z.object(schemaFields);
}

/**
 * Type for system settings form data - will be dynamically typed
 */
export type SystemSettingsFormData = Record<string, unknown>;

/**
 * Creates default form values based on raw settings
 */
export function createSystemSettingsDefaults(
  rawSettings: Record<string, RawSetting>,
): SystemSettingsFormData {
  const defaults: SystemSettingsFormData = {};

  Object.entries(rawSettings).forEach(([key, setting]) => {
    defaults[key] = setting.value;
  });

  return defaults;
}

/**
 * Validates that all required settings are present and valid
 */
export function validateSystemSettings(
  formData: SystemSettingsFormData,
  rawSettings: Record<string, RawSetting>,
): { isValid: boolean; errors: Record<string, string> } {
  const errors: Record<string, string> = {};

  Object.entries(rawSettings).forEach(([key, setting]) => {
    const value = formData[key];

    // Check if the setting is editable (if not, we skip validation)
    if (!setting.can_edit) {
      return;
    }

    // Validate based on type
    switch (setting.type) {
      case 'str':
        if (value === null || value === undefined || (typeof value === 'string' && value.trim() === '')) {
          errors[key] = `${setting.display_name || key} is required.`;
        }
        break;

      case 'int':
        if (value === null || value === undefined || value === '') {
          errors[key] = `${setting.display_name || key} is required.`;
        } else {
          const numValue = typeof value === 'string' ? parseInt(value, 10) : Number(value);
          if (Number.isNaN(numValue)) {
            errors[key] = `${setting.display_name || key} must be a valid number.`;
          }
        }
        break;

      case 'bool':
        // Boolean values are always valid (true/false)
        break;

      default:
        // For unknown types, just check for null/undefined
        if (value === null || value === undefined) {
          errors[key] = `${setting.display_name || key} is required.`;
        }
        break;
    }
  });

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * Utility function to get the appropriate HTML input type for a setting
 */
export function getInputType(fieldType: string): string {
  const mapping: Record<string, string> = {
    int: 'number',
    str: 'text',
    bool: 'checkbox', // Though we use ToggleSwitch for booleans
  };
  return mapping[fieldType] || 'text';
}
