import { ref, computed, type Ref } from 'vue';
import { useToast } from 'primevue/usetoast';
import type { FormSubmitEvent } from '@primevue/forms/form';

/**
 * Composable for common form validation patterns and error handling
 */
export function useFormValidation() {
  const toast = useToast();
  const isSubmitting = ref(false);

  /**
   * Handles form submission with common error handling
   */
  async function handleFormSubmit<T = any>(
    event: FormSubmitEvent,
    submitFn: (data: T) => Promise<{ success: boolean; error?: string; message?: string }>,
    options?: {
      successMessage?: string;
      errorMessage?: string;
      resetOnSuccess?: boolean;
    },
  ): Promise<boolean> {
    if (!event.valid) {
      toast.add({
        severity: 'error',
        summary: 'Validation Error',
        detail: 'Please correct the errors in the form.',
        life: 3000,
      });
      return false;
    }

    isSubmitting.value = true;

    try {
      const result = await submitFn(event.values as T);

      if (result.success) {
        toast.add({
          severity: 'success',
          summary: 'Success',
          detail: result.message || options?.successMessage || 'Operation completed successfully',
          life: 3000,
        });

        if (options?.resetOnSuccess !== false) {
          event.reset();
        }

        return true;
      }
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: result.error || options?.errorMessage || 'Operation failed',
        life: 5000,
      });

      return false;
    } catch (error) {
      console.error('Form submission error:', error);
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: 'An unexpected error occurred',
        life: 5000,
      });

      return false;
    } finally {
      isSubmitting.value = false;
    }
  }

  /**
   * Validates form and shows appropriate error messages
   */
  function validateForm(form: any): boolean {
    if (!form.valid) {
      toast.add({
        severity: 'error',
        summary: 'Validation Error',
        detail: 'Please correct the errors in the form.',
        life: 3000,
      });
      return false;
    }
    return true;
  }

  /**
   * Shows a success toast message
   */
  function showSuccess(message: string, summary = 'Success') {
    toast.add({
      severity: 'success',
      summary,
      detail: message,
      life: 3000,
    });
  }

  /**
   * Shows an error toast message
   */
  function showError(message: string, summary = 'Error') {
    toast.add({
      severity: 'error',
      summary,
      detail: message,
      life: 5000,
    });
  }

  /**
   * Shows a warning toast message
   */
  function showWarning(message: string, summary = 'Warning') {
    toast.add({
      severity: 'warn',
      summary,
      detail: message,
      life: 4000,
    });
  }

  /**
   * Shows an info toast message
   */
  function showInfo(message: string, summary = 'Info') {
    toast.add({
      severity: 'info',
      summary,
      detail: message,
      life: 4000,
    });
  }

  return {
    // State
    isSubmitting: computed(() => isSubmitting.value),

    // Methods
    handleFormSubmit,
    validateForm,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
}

/**
 * Composable for handling async operations with loading state
 */
export function useAsyncOperation() {
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function execute<T>(
    operation: () => Promise<T>,
    options?: {
      loadingMessage?: string;
      successMessage?: string;
      errorMessage?: string;
    },
  ): Promise<T | null> {
    isLoading.value = true;
    error.value = null;

    try {
      const result = await operation();

      if (options?.successMessage) {
        const toast = useToast();
        toast.add({
          severity: 'success',
          summary: 'Success',
          detail: options.successMessage,
          life: 3000,
        });
      }

      return result;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unexpected error occurred';
      error.value = errorMessage;

      const toast = useToast();
      toast.add({
        severity: 'error',
        summary: 'Error',
        detail: options?.errorMessage || errorMessage,
        life: 5000,
      });

      return null;
    } finally {
      isLoading.value = false;
    }
  }

  function reset() {
    isLoading.value = false;
    error.value = null;
  }

  return {
    // State
    isLoading: computed(() => isLoading.value),
    error: computed(() => error.value),

    // Methods
    execute,
    reset,
  };
}

/**
 * Composable for managing form field errors
 */
export function useFieldErrors() {
  const errors = ref<Record<string, string>>({});

  function setError(field: string, message: string) {
    errors.value[field] = message;
  }

  function clearError(field: string) {
    delete errors.value[field];
  }

  function clearAllErrors() {
    errors.value = {};
  }

  function hasError(field: string): boolean {
    return field in errors.value;
  }

  function getError(field: string): string | undefined {
    return errors.value[field];
  }

  return {
    // State
    errors: computed(() => errors.value),

    // Methods
    setError,
    clearError,
    clearAllErrors,
    hasError,
    getError,
  };
}
