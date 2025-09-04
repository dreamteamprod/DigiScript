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
    value: any;
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
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
  errors?: Record<string, string[]>;
}

/**
 * Form submission handler function type
 */
export type FormSubmitHandler<T = any> = (
  data: T
) => Promise<ApiResponse<any>>;

/**
 * Enhanced form submit event with additional utilities
 */
export interface EnhancedFormSubmitEvent<T = Record<string, any>> extends FormSubmitEvent {
  values: T;
}

/**
 * Form configuration for dynamic forms
 */
export interface DynamicFormConfig {
  fields: FormFieldConfig[];
  validationRules?: Record<string, any>;
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
  values: Record<string, any>;
}

/**
 * Form action types
 */
export enum FormActionType {
  SUBMIT = 'submit',
  RESET = 'reset',
  VALIDATE = 'validate',
  SET_FIELD_VALUE = 'setFieldValue',
  SET_FIELD_ERROR = 'setFieldError',
  CLEAR_ERRORS = 'clearErrors',
}

/**
 * Form action payload
 */
export interface FormAction {
  type: FormActionType;
  payload?: any;
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
  showSuccess: (message: string, summary?: string) => void;
  showError: (message: string, summary?: string) => void;
  showWarning: (message: string, summary?: string) => void;
  showInfo: (message: string, summary?: string) => void;
  validateForm: (form: any) => boolean;
  handleFormSubmit: <T>(
    event: FormSubmitEvent,
    submitFn: FormSubmitHandler<T>,
    options?: {
      successMessage?: string;
      errorMessage?: string;
      resetOnSuccess?: boolean;
    }
  ) => Promise<boolean>;
}
