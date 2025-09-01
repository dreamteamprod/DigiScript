<template>
  <div class="rbac-resource-permissions">
    <!-- Loading state -->
    <div v-if="loading" class="text-center p-4">
      <ProgressSpinner style="width: 2rem; height: 2rem" />
      <p class="mt-2 text-sm">Loading permissions...</p>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state p-4">
      <Message severity="error" :closable="false">
        <p>{{ error }}</p>
        <Button
          label="Retry"
          icon="pi pi-refresh"
          size="small"
          class="mt-2"
          @click="loadData"
        />
      </Message>
    </div>

    <!-- Permissions table -->
    <div v-else class="permissions-content">
      <!-- Resource objects table with role permissions -->
      <DataTable
        v-if="rbacObjects && rbacObjects.length > 0"
        :value="rbacObjects"
        class="rbac-permissions-table"
        data-key="id"
        :paginator="false"
        :scrollable="true"
        scroll-height="400px"
        :loading="processing"
      >
        <!-- Dynamic columns for display fields -->
        <Column
          v-for="field in displayFields"
          :key="field"
          :field="field"
          :header="capitalizeField(field)"
          :sortable="true"
        >
          <template #body="slotProps">
            <span class="font-medium">{{ slotProps.data[field] }}</span>
          </template>
        </Column>

        <!-- Dynamic columns for each RBAC role -->
        <Column
          v-for="role in rbacRoles"
          :key="role.key"
          :header="role.label || role.key"
          style="min-width: 120px"
        >
          <template #body="slotProps">
            <div class="permission-cell">
              <!-- Grant Role Button -->
              <Button
                v-if="!hasPermission(slotProps.data, role.value)"
                label="Grant"
                icon="pi pi-plus"
                class="p-button-success p-button-sm"
                :disabled="processing"
                @click="grantRole(slotProps.data, role.value, role.key)"
              />
              <!-- Revoke Role Button -->
              <Button
                v-else
                label="Revoke"
                icon="pi pi-minus"
                class="p-button-danger p-button-sm"
                :disabled="processing"
                @click="revokeRole(slotProps.data, role.value, role.key)"
              />
            </div>
          </template>
        </Column>
      </DataTable>

      <!-- No objects available -->
      <div v-else class="no-objects p-4">
        <Message severity="info" :closable="false">
          <p>No objects available for this resource type.</p>
        </Message>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useToast } from 'primevue/usetoast';

// PrimeVue components
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Button from 'primevue/button';
import Message from 'primevue/message';
import ProgressSpinner from 'primevue/progressspinner';

// Props and emits
interface Props {
  resource: string;
  userId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  'permissions-changed': [];
}>();

// Composables
const toast = useToast();

// Types
interface RbacObject {
  id: string;
  permissions: number;
  [key: string]: unknown;
}

interface RbacRole {
  key: string;
  label?: string;
  value: number;
}

// Reactive state
const loading = ref(true);
const processing = ref(false);
const error = ref<string>('');
const rbacObjects = ref<RbacObject[]>([]);
const displayFields = ref<string[]>([]);
const rbacRoles = ref<RbacRole[]>([]);

// Utility functions
function capitalizeField(field: string): string {
  return field.split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function hasPermission(obj: RbacObject, roleValue: number): boolean {
  // eslint-disable-next-line no-bitwise
  return (obj.permissions & roleValue) !== 0;
}

function makeURL(path: string): string {
  return `${window.location.protocol}//${window.location.hostname}:${window.location.port}${path}`;
}

// Data loading functions
async function loadRoles(): Promise<void> {
  try {
    const response = await fetch(makeURL('/api/v1/rbac/roles'), {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.ok) {
      const data = await response.json();
      rbacRoles.value = data.roles || [];
    } else {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(errorData.message || 'Failed to fetch RBAC roles');
    }
  } catch (err) {
    console.error('Error loading RBAC roles:', err);
    throw err;
  }
}

async function loadObjects(): Promise<void> {
  try {
    const searchParams = new URLSearchParams({
      resource: props.resource,
      user: props.userId,
    });

    const response = await fetch(`${makeURL('/api/v1/rbac/user/objects')}?${searchParams}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (response.ok) {
      const data = await response.json();

      // Transform the objects data structure from Vue 2 format
      // Vue 2 format: [[object, permissions], ...]
      // Vue 3 format: [{ ...object, permissions }, ...]
      if (Array.isArray(data.objects) && data.objects.length > 0) {
        rbacObjects.value = data.objects.map((item: [RbacObject, number]) => {
          const [obj, permissions] = item;
          return {
            ...obj,
            permissions,
          };
        });
      } else {
        rbacObjects.value = [];
      }

      displayFields.value = data.display_fields || [];
    } else {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(errorData.message || 'Failed to fetch RBAC objects');
    }
  } catch (err) {
    console.error('Error loading RBAC objects:', err);
    throw err;
  }
}

async function loadData(): Promise<void> {
  loading.value = true;
  error.value = '';

  try {
    await Promise.all([loadRoles(), loadObjects()]);
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Failed to load permission data';
    error.value = errorMessage;

    toast.add({
      severity: 'error',
      summary: 'Load Error',
      detail: errorMessage,
      life: 5000,
    });
  } finally {
    loading.value = false;
  }
}

// Permission management functions
async function grantRole(obj: RbacObject, roleValue: number, roleKey: string): Promise<void> {
  processing.value = true;

  try {
    const response = await fetch(makeURL('/api/v1/rbac/user/roles/grant'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        resource: props.resource,
        user: parseInt(props.userId, 10),
        object: obj,
        role: roleValue,
      }),
    });

    if (response.ok) {
      toast.add({
        severity: 'success',
        summary: 'Permission Granted',
        detail: `Successfully granted ${roleKey} role`,
        life: 3000,
      });

      // Refresh data and notify parent
      await loadObjects();
      emit('permissions-changed');
    } else {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(errorData.message || 'Failed to grant role');
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Failed to grant role';
    console.error('Error granting role:', err);

    toast.add({
      severity: 'error',
      summary: 'Grant Role Error',
      detail: errorMessage,
      life: 5000,
    });
  } finally {
    processing.value = false;
  }
}

async function revokeRole(obj: RbacObject, roleValue: number, roleKey: string): Promise<void> {
  processing.value = true;

  try {
    const response = await fetch(makeURL('/api/v1/rbac/user/roles/revoke'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        resource: props.resource,
        user: parseInt(props.userId, 10),
        object: obj,
        role: roleValue,
      }),
    });

    if (response.ok) {
      toast.add({
        severity: 'success',
        summary: 'Permission Revoked',
        detail: `Successfully revoked ${roleKey} role`,
        life: 3000,
      });

      // Refresh data and notify parent
      await loadObjects();
      emit('permissions-changed');
    } else {
      const errorData = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(errorData.message || 'Failed to revoke role');
    }
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Failed to revoke role';
    console.error('Error revoking role:', err);

    toast.add({
      severity: 'error',
      summary: 'Revoke Role Error',
      detail: errorMessage,
      life: 5000,
    });
  } finally {
    processing.value = false;
  }
}

// Lifecycle hooks
onMounted(async () => {
  await loadData();
});
</script>

<style scoped>
.rbac-resource-permissions {
  background-color: var(--surface-ground);
  color: var(--text-color);
}

/* Error state styling */
.error-state {
  text-align: center;
}

/* No objects styling */
.no-objects {
  text-align: center;
}

/* Permission cell styling */
.permission-cell {
  display: flex;
  justify-content: center;
}

/* DataTable dark theme styling */
:deep(.p-datatable) {
  background-color: var(--surface-card);
  border-color: var(--surface-border);
}

:deep(.p-datatable .p-datatable-thead > tr > th) {
  background-color: var(--surface-section);
  color: var(--text-color);
  border-color: var(--surface-border);
  font-weight: 600;
}

:deep(.p-datatable .p-datatable-tbody > tr) {
  background-color: var(--surface-card);
  color: var(--text-color);
  border-color: var(--surface-border);
}

:deep(.p-datatable .p-datatable-tbody > tr:nth-child(even)) {
  background-color: var(--surface-hover);
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
  border-color: var(--surface-border);
  padding: 0.75rem;
}

/* Button styling */
:deep(.p-button-success) {
  background-color: #28a745;
  border-color: #28a745;
  color: white;
}

:deep(.p-button-success:hover) {
  background-color: #218838;
  border-color: #1e7e34;
}

:deep(.p-button-danger) {
  background-color: #dc3545;
  border-color: #dc3545;
  color: white;
}

:deep(.p-button-danger:hover) {
  background-color: #c82333;
  border-color: #bd2130;
}

:deep(.p-button-sm) {
  font-size: 0.75rem;
  padding: 0.375rem 0.75rem;
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

/* Progress spinner */
:deep(.p-progress-spinner-circle) {
  stroke: var(--primary-color);
}

/* Scrollable table */
:deep(.p-datatable-scrollable .p-datatable-wrapper) {
  border-radius: 0.375rem;
}

/* Responsive design */
@media (max-width: 768px) {
  :deep(.p-datatable .p-datatable-tbody > tr > td) {
    padding: 0.5rem;
  }

  :deep(.p-button-sm) {
    font-size: 0.7rem;
    padding: 0.25rem 0.5rem;
  }
}
</style>
