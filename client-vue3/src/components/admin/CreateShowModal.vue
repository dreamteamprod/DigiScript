<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Setup New Show"
    :style="{ width: '500px' }"
    :closable="!isSubmitting"
    :closeOnEscape="!isSubmitting"
  >
    <Form
      v-slot="$form"
      :initialValues="initialValues"
      :resolver="resolver"
      @submit="handleSubmit"
      class="create-show-form"
    >
      <!-- Show Name Field -->
      <div class="field mb-4">
        <label for="show-name" class="font-bold">Show Name</label>
        <InputText
          id="show-name"
          name="name"
          placeholder="Enter show name"
          class="w-full"
          :class="{ 'p-invalid': $form.name?.invalid }"
          :disabled="isSubmitting"
          fluid
        />
        <Message
          v-if="$form.name?.invalid"
          severity="error"
          size="small"
          variant="simple"
        >
          {{ $form.name.error?.message }}
        </Message>
      </div>

      <!-- Start Date Field -->
      <div class="field mb-4">
        <label for="show-start" class="font-bold">Start Date</label>
        <Calendar
          id="show-start"
          name="start"
          class="w-full"
          :class="{ 'p-invalid': $form.start?.invalid }"
          dateFormat="yy-mm-dd"
          :disabled="isSubmitting"
          fluid
        />
        <Message
          v-if="$form.start?.invalid"
          severity="error"
          size="small"
          variant="simple"
        >
          {{ $form.start.error?.message }}
        </Message>
      </div>

      <!-- End Date Field -->
      <div class="field mb-4">
        <label for="show-end" class="font-bold">End Date</label>
        <Calendar
          id="show-end"
          name="end"
          class="w-full"
          :class="{ 'p-invalid': $form.end?.invalid }"
          dateFormat="yy-mm-dd"
          :disabled="isSubmitting"
          fluid
        />
        <Message
          v-if="$form.end?.invalid"
          severity="error"
          size="small"
          variant="simple"
        >
          {{ $form.end.error?.message }}
        </Message>
      </div>

      <!-- Action Buttons -->
      <div class="d-flex justify-content-between w-100 mt-4">
        <Button
          label="Cancel"
          severity="secondary"
          outlined
          type="button"
          :disabled="isSubmitting"
          @click="closeModal"
        />
        <div class="d-flex gap-2">
          <Button
            label="Save and Load"
            type="button"
            :loading="isSubmitting && saveAndLoad"
            :disabled="!$form.valid || isSubmitting"
@click="() => handleFormSubmit($form, true)"
          />
          <Button
            label="Save"
            type="submit"
            :loading="isSubmitting && !saveAndLoad"
            :disabled="!$form.valid || isSubmitting"
          />
        </div>
      </div>
    </Form>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useShowsStore } from '@/stores/shows';
import { zodResolver } from '@primevue/forms/resolvers/zod';

// PrimeVue Components
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Calendar from 'primevue/calendar';
import Form from '@primevue/forms/form';
import type { FormSubmitEvent } from '@primevue/forms/form';
import Message from 'primevue/message';

// Validation schema
import {
  createShowSchema, createShowDefaults, type CreateShowFormData,
} from '@/schemas/showValidation';

// Props
interface Props {
  modelValue: boolean;
}

const props = defineProps<Props>();

// Emits
interface Emits {
  // eslint-disable-next-line no-unused-vars
  (e: 'update:modelValue', value: boolean): void;
  // eslint-disable-next-line no-unused-vars, @typescript-eslint/no-explicit-any
  (e: 'showCreated', show: any): void;
}

const emit = defineEmits<Emits>();

// Composables
const toast = useToast();
const showsStore = useShowsStore();

// Form configuration
const initialValues = createShowDefaults;
const resolver = zodResolver(createShowSchema);

// UI state
const isSubmitting = ref(false);
const saveAndLoad = ref(false);

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

// Event handlers
function resetForm() {
  saveAndLoad.value = false;
}

function closeModal() {
  resetForm();
  visible.value = false;
}

async function createShow(formData: CreateShowFormData, loadAfterCreate: boolean) {
  // Update the store's form data
  showsStore.createShowForm = {
    name: formData.name,
    start: formData.start,
    end: formData.end,
  };

  const result = await showsStore.createShow(loadAfterCreate);

  if (result.success) {
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: `Show "${formData.name}" created successfully${loadAfterCreate ? ' and loaded' : ''}`,
      life: 3000,
    });

    emit('showCreated', result.show);
    closeModal();
  } else {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: result.error || 'Unable to create show',
      life: 5000,
    });
  }
}

async function handleSubmit(event: FormSubmitEvent): Promise<void> {
  if (!event.valid) {
    return;
  }

  const formData = event.values as CreateShowFormData;
  isSubmitting.value = true;
  saveAndLoad.value = false;

  try {
    await createShow(formData, false);
    // Reset form using the provided reset function
    event.reset();
  } catch (error) {
    console.error('Error creating show:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'An unexpected error occurred while creating the show',
      life: 5000,
    });
  } finally {
    isSubmitting.value = false;
  }
}

async function handleFormSubmit(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  form: any,
  loadAfterCreate: boolean,
) {
  if (!form.valid) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please correct the errors in the form.',
      life: 3000,
    });
    return;
  }

  const formData = form.values as CreateShowFormData;
  saveAndLoad.value = loadAfterCreate;
  isSubmitting.value = true;

  try {
    await createShow(formData, loadAfterCreate);
    // Reset form
    form.reset();
  } catch (error) {
    console.error('Error creating show:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'An unexpected error occurred while creating the show',
      life: 5000,
    });
  } finally {
    isSubmitting.value = false;
  }
}

// Watch for modal visibility changes to reset form
watch(visible, (newValue) => {
  if (newValue) {
    resetForm();
  }
});
</script>

<style scoped>
.create-show-form {
  padding: 0;
}

.field {
  margin-bottom: 1.5rem;
}

.field label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-color);
  font-weight: bold;
}

/* Dark theme form styling */
:deep(.p-inputtext) {
  background-color: var(--surface-ground);
  border-color: var(--surface-border);
  color: var(--text-color);
}

:deep(.p-inputtext:focus) {
  border-color: var(--primary-color);
  box-shadow: 0 0 0 0.2rem var(--primary-color-alpha);
}

:deep(.p-calendar .p-inputtext) {
  background-color: var(--surface-ground);
  border-color: var(--surface-border);
  color: var(--text-color);
}

/* Error styling */
:deep(.p-invalid) {
  border-color: var(--red-500) !important;
}

/* Button styling */
:deep(.p-button) {
  background-color: var(--primary-color);
  border-color: var(--primary-color);
}

:deep(.p-button:hover) {
  background-color: var(--primary-color-dark);
  border-color: var(--primary-color-dark);
}

:deep(.p-button.p-button-secondary) {
  background-color: var(--surface-500);
  border-color: var(--surface-500);
  color: var(--text-color);
}

:deep(.p-button.p-button-secondary:hover) {
  background-color: var(--surface-600);
  border-color: var(--surface-600);
}

:deep(.p-button.p-button-outlined) {
  background-color: transparent;
  color: var(--surface-500);
  border-color: var(--surface-500);
}

:deep(.p-button.p-button-outlined:hover) {
  background-color: var(--surface-500);
  color: var(--text-color-secondary);
  border-color: var(--surface-500);
}

</style>
