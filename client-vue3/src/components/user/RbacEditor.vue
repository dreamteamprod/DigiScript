<template>
  <div class="rbac-editor">
    <!-- Loading state -->
    <div v-if="loading" class="text-center p-4">
      <ProgressSpinner style="width: 3rem; height: 3rem" />
      <p class="mt-3">Loading RBAC configuration...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state p-4">
      <Message severity="error" :closable="false">
        <p><strong>Unable to load RBAC configuration</strong></p>
        <p>{{ error }}</p>
        <Button
          label="Retry"
          icon="pi pi-refresh"
          class="mt-3"
          @click="loadRbacData"
        />
      </Message>
    </div>

    <!-- RBAC configuration interface -->
    <div v-else class="rbac-content">
      <!-- User info header -->
      <div class="user-header mb-4">
        <h4 class="text-light mb-2">
          RBAC Configuration for User: <strong>{{ selectedUsername }}</strong>
        </h4>
        <p class="text-muted">
          Manage role-based access control permissions for this user across different resources.
        </p>
      </div>

      <!-- RBAC resource tabs -->
      <Tabs
        v-if="rbacResources && rbacResources.length > 0"
        v-model:value="activeTab"
        class="rbac-tabs"
      >
        <TabList>
          <Tab
            v-for="(resource, index) in rbacResources"
            :key="`rbac_resource_${resource}`"
            :value="index.toString()"
          >
            {{ capitalizeResource(resource) }}
          </Tab>
        </TabList>
        <TabPanels>
          <TabPanel
            v-for="(resource, index) in rbacResources"
            :key="`rbac_panel_${resource}`"
            :value="index.toString()"
          >
            <RbacResourcePermissions
              :resource="resource"
              :user-id="userId"
              @permissions-changed="onPermissionsChanged"
            />
          </TabPanel>
        </TabPanels>
      </Tabs>

      <!-- No resources available -->
      <div v-else class="no-resources p-4">
        <Message severity="info" :closable="false">
          <p>No RBAC resources are available for configuration.</p>
        </Message>
      </div>

      <!-- Action buttons -->
      <div class="rbac-actions mt-4">
        <div class="flex justify-content-end">
          <Button
            label="Close"
            icon="pi pi-times"
            class="p-button-secondary"
            @click="handleClose"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';

// PrimeVue components
import Tabs from 'primevue/tabs';
import TabList from 'primevue/tablist';
import Tab from 'primevue/tab';
import TabPanels from 'primevue/tabpanels';
import TabPanel from 'primevue/tabpanel';
import Button from 'primevue/button';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';

// Child components
import RbacResourcePermissions from './RbacResourcePermissions.vue';

// Props and emits
interface Props {
  userId: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  'close': [];
}>();

// Composables
const toast = useToast();
const authStore = useAuthStore();

// Reactive state
const loading = ref(true);
const error = ref<string>('');
const rbacResources = ref<string[]>([]);
const activeTab = ref<string>('0');

// Computed properties
const selectedUsername = computed(() => {
  const user = authStore.showUsers.find((u) => u.id === props.userId);
  return user ? user.username : 'Unknown User';
});

// Utility function to create API URLs (matching the Vue 2 pattern)
function makeURL(path: string): string {
  return `${window.location.protocol}//${window.location.hostname}:${window.location.port}${path}`;
}

// Utility functions
function capitalizeResource(resource: string): string {
  return resource.charAt(0).toUpperCase() + resource.slice(1);
}

// Data loading
async function loadRbacData(): Promise<void> {
  loading.value = true;
  error.value = '';

  try {
    // Fetch available RBAC resources
    const response = await fetch(`${makeURL('/api/v1/rbac/user/resources')}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.ok) {
      const data = await response.json();
      rbacResources.value = data.resources || [];

      if (rbacResources.value.length === 0) {
        console.warn('No RBAC resources available');
      }
    } else {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(errorData.message || 'Failed to fetch RBAC resources');
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Failed to load RBAC configuration';
    console.error('Error loading RBAC data:', err);
    error.value = errorMessage;

    toast.add({
      severity: 'error',
      summary: 'RBAC Configuration Error',
      detail: errorMessage,
      life: 5000,
    });
  } finally {
    loading.value = false;
  }
}

// Event handlers
function onPermissionsChanged(): void {
  // Refresh user list to reflect any permission changes
  authStore.getUsers();

  toast.add({
    severity: 'success',
    summary: 'Permissions Updated',
    detail: 'User permissions have been successfully updated',
    life: 3000,
  });
}

function handleClose(): void {
  emit('close');
}

// Lifecycle hooks
onMounted(async () => {
  await loadRbacData();
});
</script>

<style scoped>
.rbac-editor {
  padding: 1rem;
  background-color: var(--surface-ground);
  color: var(--text-color);
}

/* User header styling */
.user-header {
  border-bottom: 1px solid var(--surface-border);
  padding-bottom: 1rem;
}

.user-header h4 {
  color: var(--text-color);
  margin: 0;
}

.user-header p {
  margin: 0;
  color: var(--text-color-secondary);
}

/* Error state styling */
.error-state {
  text-align: center;
}

/* No resources styling */
.no-resources {
  text-align: center;
}

/* RBAC tabs styling */
:deep(.p-tabs) {
  background-color: var(--surface-card);
}

:deep(.p-tablist) {
  background-color: var(--surface-section);
  border-color: var(--surface-border);
}

:deep(.p-tab) {
  color: var(--text-color);
  background-color: transparent;
  border-color: var(--surface-border);
}

:deep(.p-tab[data-p-active="true"]) {
  background-color: var(--surface-card);
  border-color: var(--primary-color);
  color: var(--primary-color);
}

:deep(.p-tabpanels) {
  background-color: var(--surface-card);
  color: var(--text-color);
  border-color: var(--surface-border);
}

:deep(.p-tabpanel) {
  background-color: var(--surface-card);
}

/* Message styling */
:deep(.p-message) {
  background-color: var(--surface-card);
  border-color: var(--surface-border);
}

:deep(.p-message-error) {
  background-color: var(--red-50);
  border-color: var(--red-500);
  color: var(--red-900);
}

:deep(.p-message-info) {
  background-color: var(--blue-50);
  border-color: var(--blue-500);
  color: var(--blue-900);
}

/* Button styling */
:deep(.p-button-secondary) {
  background-color: var(--surface-500);
  border-color: var(--surface-500);
  color: var(--text-color);
}

:deep(.p-button-secondary:hover) {
  background-color: var(--surface-600);
  border-color: var(--surface-600);
}

/* Progress spinner */
:deep(.p-progress-spinner-circle) {
  stroke: var(--primary-color);
}

/* Responsive design */
@media (max-width: 768px) {
  .rbac-editor {
    padding: 0.5rem;
  }

  .user-header h4 {
    font-size: 1.1rem;
  }

  .user-header p {
    font-size: 0.9rem;
  }
}
</style>
