import { z } from 'zod';

/**
 * Zod schema for user creation form validation
 * Matches the existing validation logic in CreateUserModal.vue
 */
export const createUserSchema = z.object({
  username: z
    .string()
    .min(1, 'Username is required')
    .min(3, 'Username must be at least 3 characters')
    .trim(),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(6, 'Password must be at least 6 characters'),
  confirmPassword: z
    .string()
    .min(1, 'Please confirm your password'),
  isAdmin: z.boolean().default(false),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

/**
 * TypeScript type inferred from the schema
 */
export type CreateUserFormData = z.infer<typeof createUserSchema>;

/**
 * Default form values
 */
export const createUserDefaults: CreateUserFormData = {
  username: '',
  password: '',
  confirmPassword: '',
  isAdmin: false,
};
