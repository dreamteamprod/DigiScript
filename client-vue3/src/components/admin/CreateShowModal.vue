<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Setup New Show"
    :style="{ width: '500px' }"
    :closable="!showsStore.isSubmittingShow"
    :closeOnEscape="!showsStore.isSubmittingShow"
  >
    <form @submit.prevent="handleSave">
      <div class="field mb-4">
        <label for="show-name" class="font-bold">Show Name</label>
        <InputText
          id="show-name"
          v-model="showsStore.createShowForm.name"
          :class="{ 'p-invalid': validationErrors.name }"
          class="w-full"
          :disabled="showsStore.isSubmittingShow"
        />
        <small v-if="validationErrors.name" class="p-error">{{ validationErrors.name }}</small>
      </div>

      <div class="field mb-4">
        <label for="show-start" class="font-bold">Start Date</label>
        <Calendar
          id="show-start"
          v-model="startDate"
          :class="{ 'p-invalid': validationErrors.start }"
          class="w-full"
          dateFormat="yy-mm-dd"
          :disabled="showsStore.isSubmittingShow"
        />
        <small v-if="validationErrors.start" class="p-error">{{ validationErrors.start }}</small>
      </div>

      <div class="field mb-4">
        <label for="show-end" class="font-bold">End Date</label>
        <Calendar
          id="show-end"
          v-model="endDate"
          :class="{ 'p-invalid': validationErrors.end }"
          class="w-full"
          dateFormat="yy-mm-dd"
          :disabled="showsStore.isSubmittingShow"
        />
        <small v-if="validationErrors.end" class="p-error">{{ validationErrors.end }}</small>
      </div>
    </form>

    <template #footer>
      <div class="d-flex justify-content-between w-100">
        <Button
          label="Cancel"
          severity="secondary"
          outlined
          :disabled="showsStore.isSubmittingShow"
          @click="closeModal"
        />
        <div class="d-flex gap-2">
          <Button
            label="Save and Load"
            :loading="showsStore.isSubmittingShow && saveAndLoad"
            :disabled="showsStore.isSubmittingShow"
            @click="handleSaveAndLoad"
          />
          <Button
            label="Save"
            :loading="showsStore.isSubmittingShow && !saveAndLoad"
            :disabled="showsStore.isSubmittingShow"
            @click="handleSave"
          />
        </div>
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useShowsStore } from '@/stores/shows';

// PrimeVue Components
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Calendar from 'primevue/calendar';

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

// State
const toast = useToast();
const showsStore = useShowsStore();

const validationErrors = ref<Record<string, string>>({});
const saveAndLoad = ref(false);

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

// Methods
function formatDateForAPI(date: Date): string {
  return date.toISOString().split('T')[0];
}

const startDate = computed({
  get: () => (showsStore.createShowForm.start ? new Date(showsStore.createShowForm.start) : null),
  set: (value) => {
    showsStore.createShowForm.start = value ? formatDateForAPI(value) : '';
  },
});

const endDate = computed({
  get: () => (showsStore.createShowForm.end ? new Date(showsStore.createShowForm.end) : null),
  set: (value) => {
    showsStore.createShowForm.end = value ? formatDateForAPI(value) : '';
  },
});

function validateForm(): boolean {
  const validation = showsStore.validateCreateShowForm();
  validationErrors.value = validation.errors;
  return validation.isValid;
}

function resetForm() {
  showsStore.resetCreateShowForm();
  validationErrors.value = {};
  saveAndLoad.value = false;
}

function closeModal() {
  resetForm();
  visible.value = false;
}

async function createShow(loadAfterCreate: boolean) {
  const result = await showsStore.createShow(loadAfterCreate);

  if (result.success) {
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: `Show "${showsStore.createShowForm.name}" created successfully${loadAfterCreate ? ' and loaded' : ''}`,
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

async function handleSave() {
  if (!validateForm()) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please correct the errors in the form.',
      life: 3000,
    });
    return;
  }

  saveAndLoad.value = false;
  await createShow(false);
}

async function handleSaveAndLoad() {
  if (!validateForm()) {
    toast.add({
      severity: 'error',
      summary: 'Validation Error',
      detail: 'Please correct the errors in the form.',
      life: 3000,
    });
    return;
  }

  saveAndLoad.value = true;
  await createShow(true);
}

// Watch for modal visibility changes to reset form
watch(visible, (newValue) => {
  if (newValue) {
    resetForm();
  }
});
</script>

<style scoped>
.field {
  margin-bottom: 1.5rem;
}

.field label {
  display: block;
  margin-bottom: 0.5rem;
  color: var(--text-color);
}

.p-invalid {
  border-color: var(--red-500);
}

.p-error {
  color: var(--red-500);
  font-size: 0.875rem;
  margin-top: 0.25rem;
  display: block;
}
</style>
