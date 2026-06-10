import { ref, watch } from 'vue';
import { useUserStore } from '@/stores/user';
import type { UserSettings } from '@/types/api/user';

export const PER_PAGE_OPTIONS = [
  { value: 10, text: '10' },
  { value: 15, text: '15' },
  { value: 25, text: '25' },
  { value: 50, text: '50' },
  { value: 0, text: 'All' },
] as const;

export function usePagination(defaultPerPage = 15, tableKey?: string) {
  const userStore = useUserStore();

  const storedValue = tableKey
    ? ((userStore.userSettings as UserSettings).table_page_sizes?.[tableKey] ?? defaultPerPage)
    : defaultPerPage;

  const perPage = ref(storedValue);
  const currentPage = ref(1);

  watch(perPage, (newValue) => {
    currentPage.value = 1;
    if (tableKey) {
      userStore.updateTablePageSize(tableKey, newValue);
    }
  });

  return { perPage, currentPage };
}
