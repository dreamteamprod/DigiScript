<template>
  <b-table-simple>
    <b-tr v-for="key in orderedKeys" :key="key">
      <b-th>{{ key }}</b-th>
      <b-td>{{ tableData[key] != null ? tableData[key] : 'N/A' }}</b-td>
    </b-tr>
  </b-table-simple>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { mapActions, mapGetters } from 'vuex';
import { titleCase } from '@/js/utils';

export default defineComponent({
  name: 'AboutUser',
  computed: {
    tableData(): Record<string, unknown> {
      const data: Record<string, unknown> = {};
      Object.keys((this as any).CURRENT_USER).forEach((key) => {
        data[titleCase(key, '_')] = (this as any).CURRENT_USER[key];
      });
      return data;
    },
    orderedKeys(): string[] {
      return Object.keys(this.tableData).sort();
    },
    ...mapGetters(['CURRENT_USER']),
  },
  async beforeMount(): Promise<void> {
    await (this as any).GET_CURRENT_USER();
  },
  methods: {
    titleCase,
    ...mapActions(['GET_CURRENT_USER']),
  },
});
</script>
