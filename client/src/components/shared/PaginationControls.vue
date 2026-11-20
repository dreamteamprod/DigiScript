<template>
  <div
    v-if="totalRows > minPerPageOption"
    class="d-flex align-items-center justify-content-center gap-3 mt-2 mb-3"
  >
    <div class="d-flex align-items-center gap-2">
      <label class="mb-0 text-nowrap" :for="selectId">Rows per page</label>
      <BFormSelect
        :id="selectId"
        v-model="perPage"
        :options="PER_PAGE_OPTIONS"
        size="sm"
        style="width: auto"
      />
    </div>
    <BPagination
      v-show="perPage > 0 && totalRows > perPage"
      v-model="currentPage"
      :total-rows="totalRows"
      :per-page="perPage"
      :aria-controls="ariaControls"
      class="mb-0"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { PER_PAGE_OPTIONS } from '@/composables/usePagination';

const props = withDefaults(
  defineProps<{
    totalRows: number;
    ariaControls?: string;
  }>(),
  { ariaControls: undefined }
);

const perPage = defineModel<number>('perPage', { required: true });
const currentPage = defineModel<number>('currentPage', { required: true });

const selectId = computed(() =>
  props.ariaControls ? `${props.ariaControls}-per-page` : 'per-page-select'
);

const minPerPageOption = Math.min(
  ...PER_PAGE_OPTIONS.filter((o) => o.value > 0).map((o) => o.value)
);
</script>

<style scoped>
:deep(.pagination) {
  margin-bottom: 0;
}
</style>
