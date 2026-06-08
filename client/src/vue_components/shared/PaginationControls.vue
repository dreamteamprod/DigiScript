<template>
  <div
    v-if="showControls"
    class="d-flex align-items-center justify-content-center mt-2 mb-3"
    style="gap: 1rem"
  >
    <div class="d-flex align-items-center" style="gap: 0.5rem">
      <label class="mb-0 text-nowrap" :for="selectId">Rows per page</label>
      <b-form-select
        :id="selectId"
        :value="perPage"
        :options="perPageOptions"
        size="sm"
        style="width: auto"
        @change="$emit('update:perPage', $event)"
      />
    </div>
    <b-pagination
      v-show="perPage > 0 && totalRows > perPage"
      class="mb-0"
      :value="currentPage"
      :total-rows="totalRows"
      :per-page="perPage"
      :aria-controls="ariaControls"
      @change="$emit('update:currentPage', $event)"
    />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';

export const PER_PAGE_OPTIONS = [
  { value: 10, text: '10' },
  { value: 15, text: '15' },
  { value: 25, text: '25' },
  { value: 50, text: '50' },
  { value: 0, text: 'All' },
];

const MIN_PER_PAGE = Math.min(...PER_PAGE_OPTIONS.filter((o) => o.value > 0).map((o) => o.value));

export default defineComponent({
  name: 'PaginationControls',
  props: {
    perPage: {
      type: Number,
      required: true,
    },
    currentPage: {
      type: Number,
      required: true,
    },
    totalRows: {
      type: Number,
      required: true,
    },
    ariaControls: {
      type: String,
      default: undefined,
    },
  },
  emits: ['update:perPage', 'update:currentPage'],
  data() {
    return {
      perPageOptions: PER_PAGE_OPTIONS,
    };
  },
  computed: {
    selectId(): string {
      return this.ariaControls ? `${this.ariaControls}-per-page` : 'per-page-select';
    },
    showControls(): boolean {
      return this.totalRows > MIN_PER_PAGE;
    },
  },
});
</script>
