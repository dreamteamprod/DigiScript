<template>
  <FormField
    :name="name"
    :label="label"
    :help-text="helpText"
    :required="required"
    :disabled="disabled"
    :has-error="hasError"
    :error-message="errorMessage"
  >
    <template #default="{ fieldId, errorClass }">
      <Password
        :id="fieldId"
        :name="name"
        :placeholder="placeholder"
        :disabled="disabled"
        :class="errorClass"
        :feedback="showFeedback"
        :toggle-mask="toggleMask"
        class="w-full"
        fluid
      />
    </template>
  </FormField>
</template>

<script setup lang="ts">
import Password from 'primevue/password';
import FormField from './FormField.vue';

interface Props {
  /** The field name */
  name: string;
  /** Field label */
  label?: string;
  /** Placeholder text */
  placeholder?: string;
  /** Help text to show in tooltip */
  helpText?: string;
  /** Whether the field is required */
  required?: boolean;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Whether to show password strength feedback */
  showFeedback?: boolean;
  /** Whether to show toggle mask button */
  toggleMask?: boolean;
  /** Error message from form validation */
  errorMessage?: string;
  /** Whether the field has an error */
  hasError?: boolean;
}

withDefaults(defineProps<Props>(), {
  label: undefined,
  placeholder: undefined,
  helpText: undefined,
  required: false,
  disabled: false,
  showFeedback: false,
  toggleMask: true,
  errorMessage: undefined,
  hasError: false,
});
</script>
