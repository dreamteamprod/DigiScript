import { computed } from 'vue';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import { snapshotPageToScriptLines, type DraftScriptLine } from '@/js/yjs/draftAdapter';

/**
 * The draft's pages as the script components consume them. Pure reads over the store's
 * per-page snapshots (which are only ever replaced for a page that changed), so nothing
 * here holds a Yjs object.
 *
 * The server keeps the doc ending in an empty trailing page, so `maxPage` is the highest
 * page that *exists* — navigation must stop there, because a client can't create a page
 * (two editors creating the same new page would silently lose one editor's lines).
 */
export function useDraftPages() {
  const store = useScriptDraftStore();

  /** Existing page numbers, ascending. Non-page keys are ignored. */
  const pageNumbers = computed<number[]>(() =>
    Object.keys(store.pageSnapshots)
      .filter((key) => /^[1-9]\d*$/.test(key))
      .map(Number)
      .sort((a, b) => a - b)
  );

  /** The highest existing page (the empty trailing page, once synced); 1 before any sync. */
  const maxPage = computed<number>(() => pageNumbers.value.at(-1) ?? 1);

  function linesFor(page: number): DraftScriptLine[] {
    return snapshotPageToScriptLines(page, store.getPageSnapshot(page));
  }

  /**
   * The line before `index` on `page`, walking back across pages (skipping empty ones)
   * so act/scene headings are suppressed correctly at a page boundary. Null at the very
   * start of the script.
   */
  function previousLineOf(page: number, index: number): DraftScriptLine | null {
    const onPage = store.getPageSnapshot(page);
    if (index > 0 && onPage[index - 1]) {
      return snapshotPageToScriptLines(page, [onPage[index - 1]])[0];
    }
    for (let p = page - 1; p >= 1; p -= 1) {
      const lines = store.getPageSnapshot(p);
      if (lines.length > 0) {
        return snapshotPageToScriptLines(p, [lines[lines.length - 1]])[0];
      }
    }
    return null;
  }

  return { pageNumbers, maxPage, linesFor, previousLineOf };
}
