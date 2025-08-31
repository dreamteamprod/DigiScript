<template>
  <div class="about-user">
    <DataTable
      :value="userDataArray"
      show-gridlines
      class="p-datatable-sm"
      responsive-layout="scroll"
    >
      <Column field="label" header="Property" style="width: 40%"></Column>
      <Column field="value" header="Value">
        <template #body="slotProps">
          {{ slotProps.data.value != null ? slotProps.data.value : 'N/A' }}
        </template>
      </Column>
    </DataTable>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import DataTable from 'primevue/datatable';
import Column from 'primevue/column';
import { useAuthStore } from '../../stores/auth';

const authStore = useAuthStore();

// Utility function to convert snake_case to Title Case
function titleCase(str: string, separator: string = '_'): string {
  return str
    .split(separator)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ');
}

// Transform user data into table format
const userDataArray = computed(() => {
  const user = authStore.currentUser;
  if (!user) return [];

  const data: Array<{ label: string; value: unknown }> = [];

  // Convert user object keys to title case and create table rows
  Object.keys(user).forEach((key) => {
    data.push({
      label: titleCase(key, '_'),
      value: user[key as keyof typeof user],
    });
  });

  // Sort alphabetically by label
  return data.sort((a, b) => a.label.localeCompare(b.label));
});

// Load current user data on mount
onMounted(async () => {
  if (!authStore.currentUser) {
    await authStore.getCurrentUser();
  }
});
</script>

<style scoped>
.about-user {
  max-width: 600px;
}

:deep(.p-datatable-sm .p-datatable-thead > tr > th) {
  padding: 0.5rem 0.75rem;
}

:deep(.p-datatable-sm .p-datatable-tbody > tr > td) {
  padding: 0.5rem 0.75rem;
}
</style>
