<template>
  <div class="d-flex align-items-center justify-content-center gap-3 mt-2">
    <div class="d-flex align-items-center gap-2">
      <label class="mb-0 text-nowrap">Rows per page</label>
      <BFormSelect v-model="perPage" :options="PER_PAGE_OPTIONS" size="sm" style="width: auto" />
    </div>
    <BPagination
      v-show="perPage > 0"
      v-model="currentPage"
      :total-rows="totalRows"
      :per-page="perPage"
      :aria-controls="ariaControls"
    />
  </div>
</template>

<script setup lang="ts">
import { PER_PAGE_OPTIONS } from '@/composables/usePagination';

withDefaults(
  defineProps<{
    totalRows: number;
    ariaControls?: string;
  }>(),
  { ariaControls: undefined }
);

const perPage = defineModel<number>('perPage', { required: true });
const currentPage = defineModel<number>('currentPage', { required: true });
</script>
