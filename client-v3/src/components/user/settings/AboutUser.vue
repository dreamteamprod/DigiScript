<template>
  <BTableSimple class="w-100">
    <BTbody>
      <BTr v-for="key in orderedKeys" :key="key">
        <BTh>{{ key }}</BTh>
        <BTd>{{ tableData[key] != null ? tableData[key] : 'N/A' }}</BTd>
      </BTr>
    </BTbody>
  </BTableSimple>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useUserStore } from '@/stores/user';
import { titleCase } from '@/js/utils';

const userStore = useUserStore();

const tableData = computed(() => {
  if (!userStore.currentUser) return {} as Record<string, unknown>;
  return Object.fromEntries(
    Object.entries(userStore.currentUser).map(([k, v]) => [titleCase(k, '_'), v])
  ) as Record<string, unknown>;
});

const orderedKeys = computed(() => Object.keys(tableData.value).sort());

onMounted(() => userStore.getCurrentUser());
</script>
