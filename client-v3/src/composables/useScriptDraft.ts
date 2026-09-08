import { onMounted, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import type { SnapshotLine } from '@/js/yjs/yjsSnapshot';
import type * as Y from 'yjs';

// Module-level, not per-composable-instance: Phase 3 is expected to have more than
// one component mounting this composable at once (an editor plus a presence panel).
// Without a refcount, the second mount's join would be ignored (fine) but the
// *first* unmount would tear the room down for both — whoever happens to unmount
// first kills it for every other consumer.
let activeConsumers = 0;

/**
 * Joins the active revision's collaborative draft room on mount and leaves it on
 * unmount (once every consumer has unmounted), exposing the store's reactive collab
 * state plus a plain-object page snapshot for read paths. Editing (Phase 3) writes
 * directly to the live Y.Doc via `getDraftYdoc()`, not through the snapshot returned
 * here.
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
    activeConsumers += 1;
    if (activeConsumers === 1) {
      store.joinScriptRoom();
    }
  });

  onBeforeUnmount(() => {
    activeConsumers = Math.max(0, activeConsumers - 1);
    if (activeConsumers === 0) {
      store.leaveScriptRoom();
    }
  });

  function getPageSnapshot(page: number | string): SnapshotLine[] {
    return store.getPageSnapshot(page);
  }

  function getDraftYdoc(): Y.Doc | null {
    return store.getDraftYdoc();
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
    getDraftYdoc,
    saveDraft: store.saveDraft,
    discardDraft: store.discardDraft,
  };
}
