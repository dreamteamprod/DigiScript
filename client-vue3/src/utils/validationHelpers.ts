import { z } from 'zod';

/**
 * Common validation patterns and utilities for use with Zod schemas
 */

/**
 * Email validation regex (more permissive than the HTML5 email type)
 */
export const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

/**
 * Strong password validation regex
 * Requires at least 8 characters with at least one uppercase, lowercase, number, and special character
 */
export const STRONG_PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$/;

/**
 * Phone number validation (US format)
 */
export const PHONE_REGEX = /^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$/;

/**
 * Common Zod schema patterns
 */
export const commonSchemas = {
  /** Required string with minimum length */
  requiredString: (minLength = 1, message = 'This field is required') => z.string().min(minLength, message).trim(),

  /** Email validation */
  email: () => z.string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address')
    .trim(),

  /** Strong password validation */
  strongPassword: () => z.string()
    .min(8, 'Password must be at least 8 characters')
    .regex(
      STRONG_PASSWORD_REGEX,
      'Password must contain at least one uppercase letter, lowercase letter, number, and special character',
    ),

  /** Simple password validation */
  simplePassword: (minLength = 6) => z.string()
    .min(1, 'Password is required')
    .min(minLength, `Password must be at least ${minLength} characters`),

  /** Username validation */
  username: (minLength = 3, maxLength = 50) => z.string()
    .min(1, 'Username is required')
    .min(minLength, `Username must be at least ${minLength} characters`)
    .max(maxLength, `Username must be less than ${maxLength} characters`)
    .regex(/^[a-zA-Z0-9_-]+$/, 'Username can only contain letters, numbers, underscores, and hyphens')
    .trim(),

  /** Phone number validation */
  phone: () => z.string()
    .min(1, 'Phone number is required')
    .regex(PHONE_REGEX, 'Please enter a valid phone number'),

  /** URL validation */
  url: () => z.string()
    .min(1, 'URL is required')
    .url('Please enter a valid URL'),

  /** Date string validation (YYYY-MM-DD format) */
  dateString: () => z.string()
    .min(1, 'Date is required')
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format')
    .refine((dateStr) => {
      const date = new Date(dateStr);
      return !Number.isNaN(date.getTime());
    }, 'Please enter a valid date'),

  /** Positive integer validation */
  positiveInteger: () => z.union([z.string(), z.number()])
    .transform((val) => {
      const num = typeof val === 'string' ? parseInt(val, 10) : val;
      return Number.isNaN(num) ? val : num;
    })
    .pipe(
      z.number({ message: 'Must be a valid number' })
        .int('Must be a whole number')
        .positive('Must be a positive number'),
    ),

  /** Non-negative integer validation */
  nonNegativeInteger: () => z.union([z.string(), z.number()])
    .transform((val) => {
      const num = typeof val === 'string' ? parseInt(val, 10) : val;
      return Number.isNaN(num) ? val : num;
    })
    .pipe(
      z.number({ message: 'Must be a valid number' })
        .int('Must be a whole number')
        .min(0, 'Must be zero or positive'),
    ),

  /** Boolean with optional string conversion */
  booleanField: () => z.union([z.boolean(), z.string()])
    .transform((val) => {
      if (typeof val === 'string') {
        return val.toLowerCase() === 'true';
      }
      return val;
    })
    .pipe(z.boolean()),
};

/**
 * Create a confirm password field that validates against a password field
 */
export function createConfirmPasswordField(passwordFieldName = 'password', message = 'Passwords do not match') {
  return z.string()
    .min(1, 'Please confirm your password');
}

/**
 * Add password confirmation validation to a schema
 */
export function addPasswordConfirmation<T extends z.ZodRawShape>(
  schema: z.ZodObject<T>,
  passwordField = 'password',
  confirmField = 'confirmPassword',
  message = 'Passwords do not match',
) {
  return schema.refine((data) => data[passwordField] === data[confirmField], {
    message,
    path: [confirmField],
  });
}

/**
 * Create a date range validation (start date must be before end date)
 */
export function createDateRangeValidation<T extends z.ZodRawShape>(
  schema: z.ZodObject<T>,
  startDateField = 'startDate',
  endDateField = 'endDate',
  message = 'Start date must be before or equal to end date',
) {
  return schema.refine((data) => {
    const startDate = new Date(data[startDateField] as string);
    const endDate = new Date(data[endDateField] as string);
    return startDate <= endDate;
  }, {
    message,
    path: [startDateField],
  });
}

/**
 * Utility to format validation errors for display
 */
export function formatValidationError(error: z.ZodError): Record<string, string> {
  const formattedErrors: Record<string, string> = {};

  error.errors.forEach((err) => {
    const path = err.path.join('.');
    if (!formattedErrors[path]) {
      formattedErrors[path] = err.message;
    }
  });

  return formattedErrors;
}

/**
 * Utility to check if a string is a valid date
 */
export function isValidDate(dateString: string): boolean {
  const date = new Date(dateString);
  return !Number.isNaN(date.getTime());
}

/**
 * Utility to format date for API (YYYY-MM-DD)
 */
export function formatDateForAPI(date: Date): string {
  return date.toISOString().split('T')[0];
}

/**
 * Utility to parse date from API string
 */
export function parseDateFromAPI(dateString: string): Date {
  return new Date(dateString);
}
