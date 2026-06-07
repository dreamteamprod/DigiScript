import { defineComponent } from 'vue';

export default defineComponent({
  data() {
    return {
      rowsPerPage: 15 as number,
      currentPage: 1 as number,
    };
  },
  watch: {
    rowsPerPage(this: { currentPage: number }) {
      this.currentPage = 1;
    },
  },
});
