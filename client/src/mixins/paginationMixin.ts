import { defineComponent } from 'vue';
import type { UserSettings } from '@/types/api/user';

export default defineComponent({
  data() {
    return {
      rowsPerPage: 15 as number,
      currentPage: 1 as number,
      tableKey: '' as string,
    };
  },
  watch: {
    rowsPerPage(
      this: {
        currentPage: number;
        tableKey: string;
        $store: { dispatch: (a: string, p: unknown) => void };
      },
      newValue: number
    ) {
      this.currentPage = 1;
      if (this.tableKey) {
        this.$store.dispatch('UPDATE_TABLE_PAGE_SIZE', {
          tableKey: this.tableKey,
          value: newValue,
        });
      }
    },
  },
  created() {
    if (this.tableKey) {
      const settings = this.$store.getters.USER_SETTINGS as UserSettings | null;
      const stored = settings?.table_page_sizes?.[this.tableKey];
      if (stored != null) {
        this.rowsPerPage = stored;
      }
    }
  },
});
