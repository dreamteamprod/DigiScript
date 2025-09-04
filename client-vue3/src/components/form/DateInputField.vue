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
      <Calendar
        :id="fieldId"
        :name="name"
        :date-format="dateFormat"
        :disabled="disabled"
        :class="errorClass"
        :show-time="showTime"
        :time-only="timeOnly"
        :show-button-bar="showButtonBar"
        :selection-mode="selectionMode"
        class="w-full"
        fluid
      />
    </template>
  </FormField>
</template>

<script setup lang="ts">
import Calendar from 'primevue/calendar';
import FormField from './FormField.vue';

interface Props {
  /** The field name */
  name: string;
  /** Field label */
  label?: string;
  /** Help text to show in tooltip */
  helpText?: string;
  /** Whether the field is required */
  required?: boolean;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Date format pattern */
  dateFormat?: string;
  /** Whether to show time selection */
  showTime?: boolean;
  /** Whether to show only time (no date) */
  timeOnly?: boolean;
  /** Whether to show button bar */
  showButtonBar?: boolean;
  /** Selection mode */
  selectionMode?: 'single' | 'multiple' | 'range';
  /** Error message from form validation */
  errorMessage?: string;
  /** Whether the field has an error */
  hasError?: boolean;
}

withDefaults(defineProps<Props>(), {
  label: undefined,
  helpText: undefined,
  required: false,
  disabled: false,
  dateFormat: 'yy-mm-dd',
  showTime: false,
  timeOnly: false,
  showButtonBar: false,
  selectionMode: 'single',
  errorMessage: undefined,
  hasError: false,
});
</script>
