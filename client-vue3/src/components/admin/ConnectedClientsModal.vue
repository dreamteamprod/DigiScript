<template>
  <Dialog
    v-model:visible="visible"
    modal
    header="Connected Clients"
    :style="{ width: '800px' }"
  >
    <div v-if="loading" class="d-flex justify-content-center align-items-center py-4">
      <ProgressSpinner />
    </div>

    <div v-else-if="settingsStore.connectedClients.length === 0" class="text-center py-4">
      <p class="text-muted">No clients currently connected.</p>
    </div>

    <div v-else class="overflow-auto">
      <DataTable
        :value="settingsStore.connectedClients"
        :paginator="settingsStore.connectedClients.length > perPage"
        :rows="perPage"
        class="p-datatable-sm"
        :loading="loading"
      >
        <Column field="internal_id" header="UUID" :sortable="true" style="width: 300px;">
          <template #body="slotProps">
            <code class="small">{{ slotProps.data.internal_id }}</code>
          </template>
        </Column>
        <Column field="remote_ip" header="IP Address" :sortable="true" style="width: 120px;" />
        <Column field="is_editor" header="Editing Script" :sortable="true" style="width: 140px;">
          <template #body="slotProps">
            <Tag
              :value="slotProps.data.is_editor ? 'Yes' : 'No'"
              :severity="slotProps.data.is_editor ? 'success' : 'secondary'"
            />
          </template>
        </Column>
        <Column field="last_ping" header="Last Ping" :sortable="true" style="width: 140px;">
          <template #body="slotProps">
            {{ formatDateTime(slotProps.data.last_ping) }}
          </template>
        </Column>
        <Column field="last_pong" header="Last Pong" :sortable="true" style="width: 140px;">
          <template #body="slotProps">
            {{ formatDateTime(slotProps.data.last_pong) }}
          </template>
        </Column>
      </DataTable>
    </div>

    <template #footer>
      <div class="d-flex justify-content-between w-100">
        <Button
          label="Refresh"
          severity="secondary"
          outlined
          icon="pi pi-refresh"
          :loading="loading"
          @click="refreshClients"
        />
        <Button
          label="Close"
          @click="closeModal"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import {
  ref, computed, watch, onMounted, onUnmounted,
} from 'vue';
import { useToast } from 'primevue/usetoast';
import { useSettingsStore } from '@/stores/settings';

// PrimeVue Components
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import ProgressSpinner from 'primevue/progressspinner';
import Tag from 'primevue/tag';

// Props
interface Props {
  modelValue: boolean;
}

const props = defineProps<Props>();

// Emits
interface Emits {
  // eslint-disable-next-line no-unused-vars
  (e: 'update:modelValue', value: boolean): void;
}

const emit = defineEmits<Emits>();

// State
const toast = useToast();
const settingsStore = useSettingsStore();

const loading = ref(false);
const perPage = ref(5);
let refreshInterval: ReturnType<typeof setInterval> | null = null;

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

function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

function startAutoRefresh() {
  // Refresh clients every 2 seconds when modal is open
  refreshInterval = setInterval(async () => {
    if (!loading.value) {
      try {
        await settingsStore.getConnectedClients();
      } catch (error) {
        console.error('Auto-refresh error:', error);
      }
    }
  }, 2000);
}

function closeModal() {
  visible.value = false;
  stopAutoRefresh();
}

async function refreshClients() {
  loading.value = true;
  try {
    await settingsStore.getConnectedClients();
  } catch (error) {
    console.error('Error refreshing connected clients:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Unable to refresh connected clients',
      life: 5000,
    });
  } finally {
    loading.value = false;
  }
}

// Watch for modal visibility changes
watch(visible, async (newValue) => {
  if (newValue) {
    await refreshClients();
    startAutoRefresh();
  } else {
    stopAutoRefresh();
  }
});

// Cleanup on unmount
onUnmounted(() => {
  stopAutoRefresh();
});

// Load clients on component mount if modal is visible
onMounted(async () => {
  if (visible.value) {
    await refreshClients();
    startAutoRefresh();
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

code.small {
  font-size: 0.75rem;
  background-color: var(--surface-100);
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-family: 'Courier New', monospace;
}
</style>
