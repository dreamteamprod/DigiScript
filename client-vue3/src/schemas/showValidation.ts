import { z } from 'zod';

/**
 * Zod schema for show creation form validation
 * Handles name, start date, and end date validation with date comparison
 */
export const createShowSchema = z.object({
  name: z
    .string()
    .min(1, 'Show name is required')
    .max(100, 'Show name must be less than 100 characters')
    .trim(),
  start: z
    .string()
    .min(1, 'Start date is required')
    .refine((date) => {
      // Validate the date format (YYYY-MM-DD)
      const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
      if (!dateRegex.test(date)) {
        return false;
      }
      // Check if it's a valid date
      const parsedDate = new Date(date);
      return !Number.isNaN(parsedDate.getTime());
    }, 'Start date must be a valid date'),
  end: z
    .string()
    .min(1, 'End date is required')
    .refine((date) => {
      // Validate the date format (YYYY-MM-DD)
      const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
      if (!dateRegex.test(date)) {
        return false;
      }
      // Check if it's a valid date
      const parsedDate = new Date(date);
      return !Number.isNaN(parsedDate.getTime());
    }, 'End date must be a valid date'),
}).refine((data) => {
  // Cross-field validation: start date must be <= end date
  const startDate = new Date(data.start);
  const endDate = new Date(data.end);
  return startDate <= endDate;
}, {
  message: 'Start date must be before or equal to end date',
  path: ['start'], // This will show the error on the start field
});

/**
 * TypeScript type inferred from the schema
 */
export type CreateShowFormData = z.infer<typeof createShowSchema>;

/**
 * Default form values
 */
export const createShowDefaults: CreateShowFormData = {
  name: '',
  start: '',
  end: '',
};

/**
 * Utility function to format date for API
 */
export function formatDateForAPI(date: Date): string {
  return date.toISOString().split('T')[0];
}
