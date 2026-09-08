import { onMounted, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import type { SnapshotLine } from '@/js/yjs/yjsSnapshot';

/**
 * Joins the active revision's collaborative draft room on mount and leaves it on
 * unmount, exposing the store's reactive collab state plus a plain-object page
 * snapshot for read paths. Editing (Phase 3) writes directly to the live Y.Doc via
 * `store.draftYdoc`, not through the snapshot returned here.
 */
export function useScriptDraft() {
  const store = useScriptDraftStore();
  const {
    isDraftActive,
    isDraftSynced,
    isDraftSaving,
    isDraftDirty,
    draftLastSavedAt,
    lastCollabError,
    members,
    pageSaveProgress,
    deletedLineIds,
    editors,
    cutters,
  } = storeToRefs(store);

  onMounted(() => {
    store.joinScriptRoom();
  });

  onBeforeUnmount(() => {
    store.leaveScriptRoom();
  });

  function getPageSnapshot(page: number | string): SnapshotLine[] {
    return store.getPageSnapshot(page);
  }

  return {
    isDraftActive,
    isDraftSynced,
    isDraftSaving,
    isDraftDirty,
    draftLastSavedAt,
    lastCollabError,
    members,
    pageSaveProgress,
    deletedLineIds,
    editors,
    cutters,
    getPageSnapshot,
    saveDraft: store.saveDraft,
    discardDraft: store.discardDraft,
  };
}
