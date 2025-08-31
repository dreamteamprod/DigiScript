<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Load Show"
    :style="{ width: '800px' }"
    :closable="!showsStore.isSubmittingLoad"
    :closeOnEscape="!showsStore.isSubmittingLoad"
  >
    <div v-if="loading" class="d-flex justify-content-center align-items-center py-4">
      <ProgressSpinner />
    </div>

    <div v-else-if="showsStore.availableShows.length === 0" class="text-center py-4">
      <p class="text-muted">No shows available to load.</p>
    </div>

    <div v-else class="overflow-auto">
      <DataTable
        :value="showsStore.availableShows"
        :paginator="showsStore.availableShows.length > perPage"
        :rows="perPage"
        :loading="showsStore.isSubmittingLoad"
        class="p-datatable-sm"
      >
        <Column field="id" header="ID" :sortable="true" style="width: 80px;" />
        <Column field="name" header="Name" :sortable="true" />
        <Column field="start_date" header="Start Date" :sortable="true" style="width: 120px;" />
        <Column field="end_date" header="End Date" :sortable="true" style="width: 120px;" />
        <Column field="created_at" header="Created" :sortable="true" style="width: 140px;">
          <template #body="slotProps">
            {{ formatDateTime(slotProps.data.created_at) }}
          </template>
        </Column>
        <Column header="Action" style="width: 120px;">
          <template #body="slotProps">
            <Button
              label="Load Show"
              size="small"
              :loading="showsStore.isSubmittingLoad && selectedShowId === slotProps.data.id"
              :disabled="showsStore.isSubmittingLoad"
              @click="loadShow(slotProps.data)"
            />
          </template>
        </Column>
      </DataTable>
    </div>

    <template #footer>
      <Button
        label="Cancel"
        severity="secondary"
        outlined
        :disabled="showsStore.isSubmittingLoad"
        @click="closeModal"
      />
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import {
  ref, computed, watch, onMounted,
} from 'vue';
import { useToast } from 'primevue/usetoast';
import { useShowsStore } from '@/stores/shows';
import type { ShowData } from '@/stores/settings';

// PrimeVue Components
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import ProgressSpinner from 'primevue/progressspinner';

// Props
interface Props {
  modelValue: boolean;
}

const props = defineProps<Props>();

// Emits
interface Emits {
  // eslint-disable-next-line no-unused-vars
  (e: 'update:modelValue', value: boolean): void;
  // eslint-disable-next-line no-unused-vars
  (e: 'showLoaded', show: ShowData): void;
}

const emit = defineEmits<Emits>();

// State
const toast = useToast();
const showsStore = useShowsStore();

const loading = ref(false);
const perPage = ref(5);
const selectedShowId = ref<string | null>(null);

// Computed
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

// Methods
function formatDateTime(dateString: string): string {
  try {
    return new Date(dateString).toLocaleString();
  } catch {
    return dateString;
  }
}

function closeModal() {
  visible.value = false;
  selectedShowId.value = null;
}

async function loadShow(show: ShowData) {
  selectedShowId.value = show.id;

  const result = await showsStore.loadShow(show.id);

  if (result.success) {
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: `Show "${show.name}" loaded successfully`,
      life: 3000,
    });

    emit('showLoaded', show);
    closeModal();
  } else {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: result.error || 'Unable to load show',
      life: 5000,
    });
    selectedShowId.value = null;
  }
}

async function refreshShows() {
  loading.value = true;
  try {
    await showsStore.getAvailableShows();
  } catch (error) {
    console.error('Error refreshing shows:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Unable to refresh shows list',
      life: 5000,
    });
  } finally {
    loading.value = false;
  }
}

// Watch for modal visibility changes to refresh shows
watch(visible, async (newValue) => {
  if (newValue) {
    await refreshShows();
  }
});

// Load shows on component mount
onMounted(async () => {
  if (visible.value) {
    await refreshShows();
  }
});
</script>

<style scoped>
:deep(.p-datatable-sm .p-datatable-tbody > tr > td) {
  padding: 0.5rem;
}

:deep(.p-datatable-sm .p-datatable-thead > tr > th) {
  padding: 0.5rem;
}
</style>
