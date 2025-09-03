<template>
  <div class="user-management">
    <!-- Header with title and action buttons -->
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h1 class="h3 mb-0 text-light">User Management</h1>
      <Button
        label="New User"
        icon="pi pi-plus"
        class="p-button-success"
        @click="showCreateModal = true"
      />
    </div>

    <!-- Main content card -->
    <Card class="shadow">
      <template #content>
        <DataTable
          v-model:loading="loading"
          :value="showUsers"
          :paginator="false"
          data-key="id"
          class="p-datatable-sm"
          :empty-message="showUsers.length === 0 ? 'No users found' : undefined"
        >
          <!-- Username column -->
          <Column field="username" header="Username" :sortable="true">
            <template #body="slotProps">
              <span class="font-weight-medium">{{ slotProps.data.username }}</span>
            </template>
          </Column>

          <!-- Last Login column -->
          <Column field="last_login" header="Last Login" :sortable="true">
            <template #body="slotProps">
              <span v-if="slotProps.data.last_login" class="text-muted">
                {{ formatDateTime(slotProps.data.last_login) }}
              </span>
              <span v-else class="text-muted fst-italic">Never</span>
            </template>
          </Column>

          <!-- Last Seen column -->
          <Column field="last_seen" header="Last Seen" :sortable="true">
            <template #body="slotProps">
              <span v-if="slotProps.data.last_seen" class="text-muted">
                {{ formatDateTime(slotProps.data.last_seen) }}
              </span>
              <span v-else class="text-muted fst-italic">Never</span>
            </template>
          </Column>

          <!-- Admin Status column -->
          <Column field="is_admin" header="Admin" :sortable="true">
            <template #body="slotProps">
              <Badge
                v-if="slotProps.data.is_admin"
                value="Yes"
                severity="success"
              />
              <Badge
                v-else
                value="No"
                severity="secondary"
              />
            </template>
          </Column>

          <!-- Actions column -->
          <Column header="" style="width: 200px">
            <template #body="slotProps">
              <div class="d-flex gap-2">
                <Button
                  label="RBAC"
                  icon="pi pi-cog"
                  class="p-button-warning p-button-sm"
                  :disabled="slotProps.data.is_admin"
                  @click="editUserRbac(slotProps.data)"
                />
                <Button
                  icon="pi pi-trash"
                  class="p-button-danger p-button-sm"
                  :disabled="slotProps.data.is_admin"
                  @click="confirmDeleteUser(slotProps.data)"
                />
              </div>
            </template>
          </Column>
        </DataTable>
      </template>
    </Card>

    <!-- Create User Modal -->
    <Dialog
      v-model:visible="showCreateModal"
      header="Add New User"
      :modal="true"
      :closable="true"
      :style="{ width: '500px' }"
      class="p-fluid"
    >
      <CreateUserModal
        @user-created="onUserCreated"
        @cancel="showCreateModal = false"
      />
    </Dialog>

    <!-- RBAC Configuration Modal -->
    <Dialog
      v-model:visible="showRbacModal"
      header="User RBAC Configuration"
      :modal="true"
      :closable="true"
      :style="{ width: '80vw', maxWidth: '1200px' }"
      class="p-fluid"
    >
      <RbacEditor
        v-if="selectedUser"
        :user-id="selectedUser.id"
        @close="showRbacModal = false"
      />
    </Dialog>

    <!-- Delete Confirmation Dialog -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import {
  ref, computed, onMounted, onUnmounted,
} from 'vue';
import { useConfirm } from 'primevue/useconfirm';
import { useToast } from 'primevue/usetoast';
import { useAuthStore } from '@/stores/auth';
import type { User } from '@/stores/auth';

// PrimeVue components
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import Badge from 'primevue/badge';
import ConfirmDialog from 'primevue/confirmdialog';

// Child components
import CreateUserModal from '@/components/user/CreateUserModal.vue';
import RbacEditor from '@/components/user/RbacEditor.vue';

// Composables
const confirm = useConfirm();
const toast = useToast();
const authStore = useAuthStore();

// Reactive state
const loading = ref(false);
const showCreateModal = ref(false);
const showRbacModal = ref(false);
const selectedUser = ref<User | null>(null);
const refreshInterval = ref<number | null>(null);

// Computed properties
const showUsers = computed(() => authStore.showUsers);

// Check if current user is admin (required for user management access)
const isAdmin = computed(() => authStore.isAdmin);

// Utility functions
function formatDateTime(dateString: string): string {
  if (!dateString) return 'Never';
  try {
    return new Date(dateString).toLocaleString();
  } catch (error) {
    console.warn('Invalid date string:', dateString);
    return 'Invalid Date';
  }
}

// User management actions
async function refreshUsers(): Promise<void> {
  if (!isAdmin.value) {
    console.warn('User management requires admin privileges');
    return;
  }

  loading.value = true;
  try {
    await authStore.getUsers();
  } catch (error) {
    console.error('Failed to refresh users:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to refresh user list',
      life: 5000,
    });
  } finally {
    loading.value = false;
  }
}

function onUserCreated(): void {
  showCreateModal.value = false;
  refreshUsers();
  toast.add({
    severity: 'success',
    summary: 'Success',
    detail: 'User created successfully',
    life: 3000,
  });
}

function editUserRbac(user: User): void {
  selectedUser.value = user;
  showRbacModal.value = true;
}

async function deleteUser(user: User): Promise<void> {
  try {
    await authStore.deleteUser(user.id);
    await refreshUsers();
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: `User "${user.username}" deleted successfully`,
      life: 3000,
    });
  } catch (error) {
    console.error('Failed to delete user:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete user',
      life: 5000,
    });
  }
}

function confirmDeleteUser(user: User): void {
  confirm.require({
    message: `Are you sure you want to delete user "${user.username}"?`,
    header: 'Delete User Confirmation',
    icon: 'pi pi-exclamation-triangle',
    accept: () => deleteUser(user),
    acceptLabel: 'Delete',
    acceptClass: 'p-button-danger',
    rejectLabel: 'Cancel',
  });
}

// Lifecycle hooks
onMounted(async () => {
  if (!isAdmin.value) {
    toast.add({
      severity: 'warn',
      summary: 'Access Denied',
      detail: 'User management requires administrator privileges',
      life: 5000,
    });
    return;
  }

  // Initial load
  await refreshUsers();

  // Set up auto-refresh every 5 seconds (matching Vue 2 behavior)
  refreshInterval.value = window.setInterval(refreshUsers, 5000);
});

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value);
  }
});
</script>

<style scoped>
.user-management {
  padding: 1rem;
  background-color: var(--surface-ground);
  /* Remove min-height: 100vh as this is inside a tab panel */
}

/* Dark theme styling to match Vue 2 */
:deep(.p-card) {
  background-color: var(--surface-card);
  border: 1px solid var(--surface-border);
}

:deep(.p-datatable) {
  background-color: var(--surface-card);
}

:deep(.p-datatable .p-datatable-thead > tr > th) {
  background-color: var(--surface-section);
  color: var(--text-color);
  border-color: var(--surface-border);
}

:deep(.p-datatable .p-datatable-tbody > tr) {
  background-color: var(--surface-card);
  color: var(--text-color);
}

:deep(.p-datatable .p-datatable-tbody > tr:nth-child(even)) {
  background-color: var(--surface-hover);
}

:deep(.p-datatable .p-datatable-tbody > tr > td) {
  border-color: var(--surface-border);
}

/* Button styling */
:deep(.p-button-success) {
  background-color: #28a745;
  border-color: #28a745;
}

:deep(.p-button-warning) {
  background-color: #ffc107;
  border-color: #ffc107;
  color: #000;
}

:deep(.p-button-danger) {
  background-color: #dc3545;
  border-color: #dc3545;
}

/* Badge styling */
:deep(.p-badge) {
  font-size: 0.75rem;
}

/* Modal styling */
:deep(.p-dialog) {
  background-color: var(--surface-overlay);
}

:deep(.p-dialog .p-dialog-header) {
  background-color: var(--surface-section);
  color: var(--text-color);
  border-bottom: 1px solid var(--surface-border);
}

:deep(.p-dialog .p-dialog-content) {
  background-color: var(--surface-overlay);
  color: var(--text-color);
}
</style>
