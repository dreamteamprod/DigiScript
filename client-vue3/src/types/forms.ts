import type { FormSubmitEvent } from '@primevue/forms/form';

/**
 * Common form-related TypeScript types and interfaces
 */

/**
 * Base form field configuration
 */
export interface BaseFormField {
  name: string;
  label?: string;
  required?: boolean;
  disabled?: boolean;
  readonly?: boolean;
  helpText?: string;
}

/**
 * Text input field configuration
 */
export interface TextInputField extends BaseFormField {
  type: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  placeholder?: string;
  maxLength?: number;
  minLength?: number;
}

/**
 * Select field configuration
 */
export interface SelectField extends BaseFormField {
  type: 'select' | 'multiselect';
  options: Array<{
    label: string;
    value: string | number;
    disabled?: boolean;
  }>;
  placeholder?: string;
  multiple?: boolean;
}

/**
 * Date field configuration
 */
export interface DateField extends BaseFormField {
  type: 'date' | 'datetime' | 'time';
  showTime?: boolean;
  timeOnly?: boolean;
  dateFormat?: string;
  selectionMode?: 'single' | 'multiple' | 'range';
}

/**
 * Checkbox field configuration
 */
export interface CheckboxField extends BaseFormField {
  type: 'checkbox';
  binary?: boolean;
}

/**
 * Toggle field configuration
 */
export interface ToggleField extends BaseFormField {
  type: 'toggle';
  onLabel?: string;
  offLabel?: string;
}

/**
 * Union type for all form field configurations
 */
export type FormFieldConfig =
  | TextInputField
  | SelectField
  | DateField
  | CheckboxField
  | ToggleField;

/**
 * Form validation result
 */
export interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

/**
 * API response structure for form submissions
 */
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  errors?: Record<string, string[]>;
}

/**
 * Form submission handler function type
 */
export type FormSubmitHandler<T = unknown> = (
  _formData: T
) => Promise<ApiResponse<unknown>>;

/**
 * Enhanced form submit event with additional utilities
 */
export interface EnhancedFormSubmitEvent<T = Record<string, unknown>> {
  values: T;
  valid: boolean;
  reset: () => void;
}

/**
 * Form configuration for dynamic forms
 */
export interface DynamicFormConfig {
  fields: FormFieldConfig[];
  validationRules?: Record<string, unknown>;
  submitEndpoint?: string;
  resetOnSubmit?: boolean;
  showResetButton?: boolean;
}

/**
 * Form state management
 */
export interface FormState {
  isSubmitting: boolean;
  isDirty: boolean;
  isValid: boolean;
  errors: Record<string, string>;
  values: Record<string, unknown>;
}

/**
 * Form action payload
 */
export interface FormAction {
  type: string;
  payload?: unknown;
}

/**
 * Modal form props
 */
export interface ModalFormProps {
  visible: boolean;
  title: string;
  width?: string;
  height?: string;
  closable?: boolean;
  closeOnEscape?: boolean;
  modal?: boolean;
}

/**
 * Toast notification types
 */
export type ToastSeverity = 'success' | 'info' | 'warn' | 'error';

/**
 * Toast notification configuration
 */
export interface ToastConfig {
  severity: ToastSeverity;
  summary?: string;
  detail: string;
  life?: number;
  closable?: boolean;
  sticky?: boolean;
}

/**
 * Form utilities type
 */
export interface FormUtils {
  showSuccess: (_msg: string, _sum?: string) => void;
  showError: (_msg: string, _sum?: string) => void;
  showWarning: (_msg: string, _sum?: string) => void;
  showInfo: (_msg: string, _sum?: string) => void;
  validateForm: (_frm: { valid: boolean }) => boolean;
  handleFormSubmit: <T>(
    _evt: FormSubmitEvent,
    _fn: FormSubmitHandler<T>,
    _opts?: {
      successMessage?: string;
      errorMessage?: string;
      resetOnSuccess?: boolean;
    }
  ) => Promise<boolean>;
}
