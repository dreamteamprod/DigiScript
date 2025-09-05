<template>
  <div class="ds-form-field">
    <label
      v-if="label"
      :for="fieldId"
      :class="['ds-form-field-label', { required: required }]"
    >
      {{ label }}
      <slot name="label-addon" />
    </label>

    <slot :fieldId="fieldId" :hasError="hasError" />

    <div v-if="helpText" class="ds-form-field-help">
      {{ helpText }}
    </div>

    <div v-if="hasError && errorMessage" class="ds-form-field-error">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { generateId } from '@/utils/idGenerator';

interface Props {
  label?: string;
  required?: boolean;
  helpText?: string;
  errorMessage?: string;
  hasError?: boolean;
}

withDefaults(defineProps<Props>(), {
  label: '',
  required: false,
  helpText: '',
  errorMessage: '',
  hasError: false,
});

// Generate a unique field ID for accessibility
const fieldId = computed(() => generateId('field'));
</script>

<style scoped>
/* All styles are handled by the global components.css file */
/* This component uses the .ds-form-field, .ds-form-field-label, etc. classes */
</style>
