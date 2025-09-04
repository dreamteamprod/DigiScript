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
      <InputText
        :id="fieldId"
        :name="name"
        :type="type"
        :placeholder="placeholder"
        :readonly="readonly"
        :disabled="disabled"
        :class="errorClass"
        class="w-full"
        fluid
      />
    </template>
  </FormField>
</template>

<script setup lang="ts">
import InputText from 'primevue/inputtext';
import FormField from './FormField.vue';

interface Props {
  /** The field name */
  name: string;
  /** Field label */
  label?: string;
  /** Input type */
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  /** Placeholder text */
  placeholder?: string;
  /** Help text to show in tooltip */
  helpText?: string;
  /** Whether the field is required */
  required?: boolean;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Whether the field is readonly */
  readonly?: boolean;
  /** Error message from form validation */
  errorMessage?: string;
  /** Whether the field has an error */
  hasError?: boolean;
}

withDefaults(defineProps<Props>(), {
  label: undefined,
  type: 'text',
  placeholder: undefined,
  helpText: undefined,
  required: false,
  disabled: false,
  readonly: false,
  errorMessage: undefined,
  hasError: false,
});
</script>
