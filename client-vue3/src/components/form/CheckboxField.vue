<template>
  <div class="form-field-checkbox">
    <Checkbox
      :id="fieldId"
      :name="name"
      :binary="binary"
      :disabled="disabled"
      :class="errorClass"
    />
    <label :for="fieldId" class="form-field-checkbox__label">
      {{ label }}
      <Button
        v-if="helpText"
        :id="`${fieldId}-help-btn`"
        icon="pi pi-question-circle"
        text
        rounded
        severity="secondary"
        size="small"
        class="form-field-checkbox__help-button"
        @click="showHelp"
      />
    </label>

    <Message
      v-if="hasError && errorMessage"
      severity="error"
      size="small"
      variant="simple"
      class="form-field-checkbox__error"
    >
      {{ errorMessage }}
    </Message>

    <!-- Help Tooltip -->
    <OverlayPanel v-if="helpText" ref="helpOverlay" class="form-field-checkbox__help-overlay">
      <div class="form-field-checkbox__help-content">
        {{ helpText }}
      </div>
    </OverlayPanel>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import Checkbox from 'primevue/checkbox';
import Button from 'primevue/button';
import Message from 'primevue/message';
import OverlayPanel from 'primevue/overlaypanel';

interface Props {
  /** The field name */
  name: string;
  /** Field label */
  label: string;
  /** Help text to show in tooltip */
  helpText?: string;
  /** Whether to use binary mode (true/false vs value/null) */
  binary?: boolean;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Error message from form validation */
  errorMessage?: string;
  /** Whether the field has an error */
  hasError?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  helpText: undefined,
  binary: true,
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
.form-field-checkbox {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 0.5rem;
}

.form-field-checkbox__label {
  color: var(--text-color);
  font-size: 0.875rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.form-field-checkbox__help-button {
  padding: 0.25rem;
}

.form-field-checkbox__error {
  margin-left: auto;
}

.form-field-checkbox__help-overlay {
  max-width: 300px;
}

.form-field-checkbox__help-content {
  max-width: 300px;
  line-height: 1.4;
}

/* Dark theme adjustments */
:deep(.p-checkbox) {
  background-color: var(--surface-ground);
  border-color: var(--surface-border);
}

:deep(.p-checkbox.p-checkbox-checked) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

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
