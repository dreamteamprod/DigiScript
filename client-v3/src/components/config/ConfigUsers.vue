<template>
  <BContainer fluid class="mx-0">
    <BRow>
      <BCol>
        <BTable id="users-table" :items="users" :fields="userFields" show-empty>
          <template #head(btn)>
            <BButtonGroup>
              <BButton variant="outline-success" @click="newUserModal?.show()">New User</BButton>
              <BButton variant="outline-success" @click="newAdminModal?.show()">New Admin</BButton>
            </BButtonGroup>
          </template>
          <template #head(is_admin)>User Type</template>
          <template #cell(created_on)="data">
            {{ data.item.created_on ?? 'N/A' }}
          </template>
          <template #cell(last_login)="data">
            {{ data.item.last_login ?? 'Never' }}
          </template>
          <template #cell(last_seen)="data">
            {{ data.item.last_seen ?? 'Never' }}
          </template>
          <template #cell(is_admin)="data">
            <BBadge v-if="data.item.is_admin" variant="primary">Admin</BBadge>
            <BBadge v-else variant="secondary">User</BBadge>
          </template>
          <template #cell(btn)="data">
            <BButtonGroup>
              <BButton
                variant="warning"
                :disabled="data.item.is_admin"
                @click.stop="openRbac(data.item.id)"
              >
                RBAC
              </BButton>
              <BButton
                variant="secondary"
                :disabled="data.item.id === currentUser?.id"
                @click.stop="openEditUser(data.item)"
              >
                Edit
              </BButton>
              <BButton
                variant="info"
                :disabled="data.item.id === currentUser?.id"
                @click.stop="openResetPassword(data.item)"
              >
                Reset Password
              </BButton>
              <BButton
                variant="danger"
                :disabled="
                  (adminUsers.length === 1 && data.item.is_admin) ||
                  data.item.id === currentUser?.id
                "
                @click.stop="deleteUser(data.item)"
              >
                Delete
              </BButton>
            </BButtonGroup>
          </template>
        </BTable>
      </BCol>
    </BRow>

    <BModal ref="newUserModal" title="Add New User" size="md" no-footer>
      <CreateUser :is-first-admin="false" @created_user="handleUserCreated(newUserModal)" />
    </BModal>

    <BModal ref="newAdminModal" title="Add New Admin" size="md" no-footer>
      <CreateUser
        :is-first-admin="false"
        :is-admin="true"
        @created_user="handleUserCreated(newAdminModal)"
      />
    </BModal>

    <BModal ref="rbacModal" title="User RBAC Config" size="xl" no-footer>
      <ConfigRbac v-if="selectedUserId != null" :user-id="selectedUserId" />
    </BModal>

    <BModal
      ref="editUserModal"
      title="Edit User"
      size="sm"
      @ok="submitEditUser"
      @hidden="clearEditUser"
    >
      <BForm v-if="editFormState">
        <BFormGroup label="User Type">
          <BFormCheckbox v-model="editFormState.is_admin" switch>
            {{ editFormState.is_admin ? 'Admin' : 'Standard User' }}
          </BFormCheckbox>
        </BFormGroup>
      </BForm>
    </BModal>

    <BModal ref="resetPasswordModal" title="Reset User Password" size="md" no-footer>
      <ResetPassword
        v-if="selectedUser"
        :user-id="selectedUser.id"
        :username="selectedUser.username"
        @cancel="resetPasswordModal?.hide()"
        @password-reset="userStore.getUsers()"
        @done="resetPasswordModal?.hide()"
      />
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import { BModal } from 'bootstrap-vue-next';
import { useUserStore } from '@/stores/user';
import { useConfirm } from '@/composables/useConfirm';
import CreateUser from '@/components/user/CreateUser.vue';
import ConfigRbac from '@/components/user/ConfigRbac.vue';
import ResetPassword from '@/components/user/ResetPassword.vue';

const userStore = useUserStore();
const { confirm } = useConfirm();
const { users, currentUser } = storeToRefs(userStore);

const newUserModal = ref<InstanceType<typeof BModal>>();
const newAdminModal = ref<InstanceType<typeof BModal>>();
const rbacModal = ref<InstanceType<typeof BModal>>();
const editUserModal = ref<InstanceType<typeof BModal>>();
const resetPasswordModal = ref<InstanceType<typeof BModal>>();

const selectedUserId = ref<number | null>(null);
const selectedUser = ref<{ id: number; username: string } | null>(null);
const editFormState = ref<Record<string, unknown> | null>(null);

const userFields = [
  'username',
  'created_on',
  'last_login',
  'last_seen',
  { key: 'is_admin', label: 'User Type' },
  { key: 'btn', label: '' },
];

const adminUsers = computed(() => users.value.filter((u) => u.is_admin));

function handleUserCreated(modal: InstanceType<typeof BModal> | undefined): void {
  modal?.hide();
  userStore.getUsers();
}

function openRbac(userId: number): void {
  selectedUserId.value = userId;
  rbacModal.value?.show();
}

function openResetPassword(user: { id: number; username: string }): void {
  selectedUser.value = user;
  resetPasswordModal.value?.show();
}

function openEditUser(user: Record<string, unknown>): void {
  editFormState.value = { ...user };
  editUserModal.value?.show();
}

function clearEditUser(): void {
  editFormState.value = null;
}

async function submitEditUser(): Promise<void> {
  if (editFormState.value) {
    await userStore.editUser(editFormState.value as { id: number });
  }
}

async function deleteUser(item: { id: number; username: string }): Promise<void> {
  const confirmed = await confirm(`Are you sure you want to delete ${item.username}?`, {
    title: 'Delete User',
    okVariant: 'danger',
    okTitle: 'Delete',
  });
  if (!confirmed) return;
  await userStore.deleteUser(item.id);
}

let pollTimer: ReturnType<typeof setTimeout> | null = null;

function schedulePolling(): void {
  pollTimer = setTimeout(async () => {
    await userStore.getUsers();
    schedulePolling();
  }, 5000);
}

onMounted(async () => {
  await userStore.getUsers();
  schedulePolling();
});

onBeforeUnmount(() => {
  if (pollTimer) clearTimeout(pollTimer);
});
</script>
