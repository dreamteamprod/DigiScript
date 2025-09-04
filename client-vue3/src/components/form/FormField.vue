<template>
  <div class="form-field" :class="{ 'form-field--error': hasError }">
    <label
      v-if="label"
      :for="fieldId"
      class="form-field__label"
      :class="{ 'form-field__label--required': required }"
    >
      {{ label }}
      <Button
        v-if="helpText"
        :id="`${fieldId}-help-btn`"
        icon="pi pi-question-circle"
        text
        rounded
        severity="secondary"
        size="small"
        class="form-field__help-button"
        @click="showHelp"
      />
    </label>

    <div class="form-field__input">
      <slot
        :fieldId="fieldId"
        :hasError="hasError"
        :errorClass="errorClass"
        :disabled="disabled"
      />
    </div>

    <Message
      v-if="hasError && errorMessage"
      severity="error"
      size="small"
      variant="simple"
      class="form-field__error"
    >
      {{ errorMessage }}
    </Message>

    <!-- Help Tooltip -->
    <OverlayPanel v-if="helpText" ref="helpOverlay" class="form-field__help-overlay">
      <div class="form-field__help-content">
        {{ helpText }}
      </div>
    </OverlayPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import Button from 'primevue/button';
import Message from 'primevue/message';
import OverlayPanel from 'primevue/overlaypanel';

interface Props {
  /** The field name/id */
  name: string;
  /** Field label */
  label?: string;
  /** Help text to show in tooltip */
  helpText?: string;
  /** Whether the field is required */
  required?: boolean;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Error message from form validation */
  errorMessage?: string;
  /** Whether the field has an error */
  hasError?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  label: undefined,
  helpText: undefined,
  required: false,
  disabled: false,
  errorMessage: undefined,
  hasError: false,
});

// Refs
const helpOverlay = ref();

// Computed
const fieldId = computed(() => `${props.name}-input`);
const errorClass = computed(() => ({ 'p-invalid': props.hasError }));

// Methods
function showHelp(event: Event) {
  if (helpOverlay.value && props.helpText) {
    helpOverlay.value.toggle(event);
  }
}
</script>

<style scoped>
.form-field {
  margin-bottom: 1.5rem;
}

.form-field--error {
  /* Additional styling for error state if needed */
}

.form-field__label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-color);
  font-weight: bold;
  font-size: 0.875rem;
}

.form-field__label--required::after {
  content: ' *';
  color: var(--red-500);
}

.form-field__help-button {
  margin-left: 0.5rem;
  padding: 0.25rem;
  vertical-align: middle;
}

.form-field__input {
  position: relative;
}

.form-field__error {
  margin-top: 0.25rem;
}

.form-field__help-overlay {
  max-width: 300px;
}

.form-field__help-content {
  max-width: 300px;
  line-height: 1.4;
}

/* Dark theme adjustments */
:deep(.p-button.p-button-text) {
  color: var(--text-color-secondary);
}

:deep(.p-button.p-button-text:hover) {
  color: var(--text-color);
  background-color: var(--surface-hover);
}

:deep(.p-overlaypanel) {
  background-color: var(--surface-overlay);
  color: var(--text-color);
  border: 1px solid var(--surface-border);
}

:deep(.p-overlaypanel-content) {
  background-color: var(--surface-overlay);
  color: var(--text-color);
}
</style>
