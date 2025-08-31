<template>
  <div class="stage-direction-styles">
    <div v-if="!hasShow" class="p-4">
      <Message severity="warn" :closable="false">
        No show loaded. Stage direction styles are only available when a show is loaded.
      </Message>
    </div>

    <div v-else class="space-y-4">
      <div class="flex justify-between items-center">
        <h3 class="text-lg font-semibold">Stage Direction Style Overrides</h3>
        <Button
          label="New Override"
          icon="pi pi-plus"
          outlined
          severity="success"
          @click="showNewOverrideDialog = true"
        />
      </div>

      <DataTable
        :value="tableData"
        :loading="loading"
        show-gridlines
        responsive-layout="scroll"
        class="p-datatable-sm"
        empty-message="No style overrides configured"
      >
        <Column field="description" header="Style Description" style="width: 30%">
          <template #body="slotProps">
            {{ getStyleDescription(slotProps.data.settings.id) }}
          </template>
        </Column>

        <Column header="Example" style="width: 40%">
          <template #body="slotProps">
            <i
              class="example-stage-direction"
              :style="getExampleCss(slotProps.data.settings)"
            >
              {{ formatExampleText(slotProps.data.settings) }}
            </i>
          </template>
        </Column>

        <Column style="width: 30%">
          <template #body="slotProps">
            <div class="flex gap-2">
              <Button
                icon="pi pi-pencil"
                severity="warning"
                size="small"
                outlined
                @click="editOverride(slotProps.data)"
              />
              <Button
                icon="pi pi-trash"
                severity="danger"
                size="small"
                outlined
                @click="confirmDeleteOverride(slotProps.data)"
              />
            </div>
          </template>
        </Column>
      </DataTable>
    </div>

    <!-- Placeholder dialogs for future enhancement -->
    <Dialog
      v-model:visible="showNewOverrideDialog"
      header="Add New Override"
      modal
      style="width: 50rem"
    >
      <Message severity="info">
        Stage direction style override functionality will be implemented in a future update.
        This feature allows customizing the appearance of stage directions in scripts.
      </Message>

      <template #footer>
        <Button label="Cancel" outlined @click="showNewOverrideDialog = false" />
        <Button label="Coming Soon" disabled />
      </template>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useConfirm } from 'primevue/useconfirm';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Message from 'primevue/message';
import Dialog from 'primevue/dialog';
import { useAuthStore } from '../../stores/auth';

const authStore = useAuthStore();
const confirm = useConfirm();

// Component state
const loading = ref(false);
const showNewOverrideDialog = ref(false);

// Example text for style previews
const exampleText = 'Your stage direction will look like this when formatted in the script!';

// Mock data - in the future this would come from a show store
// For now, return false to show the warning message
// In the future, this would check if there's a current show loaded
const hasShow = computed(() => false);

// Return the stage direction style overrides from auth store
const tableData = computed(() => authStore.stageDirectionStyleOverrides || []);

// Define types for better TypeScript support
interface StageDirectionSettings {
  id: string;
  bold?: boolean;
  italic?: boolean;
  underline?: boolean;
  text_colour?: string;
  text_format?: string;
  enable_background_colour?: boolean;
  background_colour?: string;
}

interface StageDirectionOverride {
  id: string;
  settings: StageDirectionSettings;
}

// Helper functions
function getStyleDescription(styleId: string): string {
  // This would look up the description from available stage direction styles
  return `Style ${styleId}`;
}

function getExampleCss(settings: StageDirectionSettings): Record<string, string> {
  const style: Record<string, string> = {
    'font-weight': settings.bold ? 'bold' : 'normal',
    'font-style': settings.italic ? 'italic' : 'normal',
    'text-decoration-line': settings.underline ? 'underline' : 'none',
    color: settings.text_colour || '#000000',
  };

  if (settings.enable_background_colour) {
    style['background-color'] = settings.background_colour || 'transparent';
  }

  return style;
}

function formatExampleText(settings: StageDirectionSettings): string {
  switch (settings.text_format) {
    case 'upper':
      return exampleText.toUpperCase();
    case 'lower':
      return exampleText.toLowerCase();
    default:
      return exampleText;
  }
}

async function deleteOverride(override: StageDirectionOverride) {
  try {
    await authStore.deleteStageDirectionStyleOverride(override.id);
  } catch (error) {
    console.error('Error deleting override:', error);
  }
}

function editOverride(override: StageDirectionOverride) {
  console.log('Edit override:', override);
  // TODO: Implement edit functionality
}

function confirmDeleteOverride(override: StageDirectionOverride) {
  confirm.require({
    message: 'Are you sure you want to delete this style override?',
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    accept: () => {
      deleteOverride(override);
    },
  });
}

// Load data on mount
onMounted(async () => {
  loading.value = true;
  try {
    await authStore.getStageDirectionStyleOverrides();
  } catch (error) {
    console.error('Error loading stage direction overrides:', error);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.example-stage-direction {
  font-style: italic;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
}

:deep(.p-datatable-sm .p-datatable-thead > tr > th) {
  padding: 0.5rem;
}

:deep(.p-datatable-sm .p-datatable-tbody > tr > td) {
  padding: 0.5rem;
}
</style>
