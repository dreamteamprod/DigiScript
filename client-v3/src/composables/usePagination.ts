import { ref, watch } from 'vue';

export const PER_PAGE_OPTIONS = [
  { value: 10, text: '10' },
  { value: 15, text: '15' },
  { value: 25, text: '25' },
  { value: 50, text: '50' },
  { value: 0, text: 'All' },
] as const;

export function usePagination(defaultPerPage = 15) {
  const perPage = ref(defaultPerPage);
  const currentPage = ref(1);

  watch(perPage, () => {
    currentPage.value = 1;
  });

  return { perPage, currentPage };
}
