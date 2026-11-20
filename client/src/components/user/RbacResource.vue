<template>
  <div v-if="!loaded" class="text-center">
    <BSpinner style="width: 10rem; height: 10rem" variant="info" />
  </div>
  <div v-else-if="error">
    <strong>Unable to load RBAC config, please try again!</strong>
  </div>
  <BContainer v-else fluid class="mx-0">
    <BRow>
      <BCol>
        <BTable
          :id="`rbac-table-${resource}`"
          :items="rbacObjects.map((x) => x[0])"
          :fields="[...displayFields, ...rbacRoles]"
          show-empty
        >
          <template v-for="role in rbacRoles" #[getCellSlot(role)]="data" :key="role">
            <BButton
              v-if="(rbacObjects[data.index][1] & rbacRolesDict[role]) === 0"
              variant="primary"
              :disabled="processing"
              @click.stop="giveRole(data.item, rbacRolesDict[role])"
            >
              Grant Role
            </BButton>
            <BButton
              v-else
              variant="danger"
              :disabled="processing"
              @click.stop="revokeRole(data.item, rbacRolesDict[role])"
            >
              Revoke Role
            </BButton>
          </template>
        </BTable>
      </BCol>
    </BRow>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';

interface RbacRole {
  key: string;
  value: number;
}

const props = defineProps<{
  resource: string;
  userId: number;
}>();

const loaded = ref(false);
const error = ref(false);
const rbacObjects = ref<Array<[unknown, number]>>([]);
const displayFields = ref<string[]>([]);
const roles = ref<RbacRole[]>([]);
const processing = ref(false);

const rbacRoles = computed(() => roles.value.map((r) => r.key));
const rbacRolesDict = computed(() => {
  const dict: Record<string, number> = {};
  roles.value.forEach((r) => {
    dict[r.key] = r.value;
  });
  return dict;
});

function getCellSlot(role: string): string {
  return `cell(${role})`;
}

async function getRoles(): Promise<void> {
  try {
    const response = await fetch(makeURL('/api/v1/rbac/roles'));
    if (response.ok) {
      const data = await response.json();
      roles.value = data.roles;
    } else {
      toast.error('Unable to fetch RBAC roles');
      error.value = true;
    }
  } catch {
    toast.error('Unable to fetch RBAC roles');
    error.value = true;
  }
}

async function getObjects(): Promise<void> {
  const params = new URLSearchParams({ resource: props.resource, user: String(props.userId) });
  try {
    const response = await fetch(`${makeURL('/api/v1/rbac/user/objects')}?${params}`);
    if (response.ok) {
      const data = await response.json();
      rbacObjects.value = data.objects;
      displayFields.value = data.display_fields;
    } else {
      toast.error('Unable to fetch RBAC objects for resource');
      error.value = true;
    }
  } catch {
    toast.error('Unable to fetch RBAC objects for resource');
    error.value = true;
  }
}

async function giveRole(object: unknown, role: number): Promise<void> {
  processing.value = true;
  try {
    const response = await fetch(makeURL('/api/v1/rbac/user/roles/grant'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resource: props.resource, user: props.userId, object, role }),
    });
    if (response.ok) toast.success('Granted role to user');
    else toast.error('Unable to grant role to user');
  } catch {
    toast.error('Unable to grant role to user');
  }
  await getObjects();
  processing.value = false;
}

async function revokeRole(object: unknown, role: number): Promise<void> {
  processing.value = true;
  try {
    const response = await fetch(makeURL('/api/v1/rbac/user/roles/revoke'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resource: props.resource, user: props.userId, object, role }),
    });
    if (response.ok) toast.success('Revoked role from user');
    else toast.error('Unable to revoke role from user');
  } catch {
    toast.error('Unable to revoke role from user');
  }
  await getObjects();
  processing.value = false;
}

onMounted(async () => {
  await Promise.all([getObjects(), getRoles()]);
  loaded.value = true;
});
</script>
