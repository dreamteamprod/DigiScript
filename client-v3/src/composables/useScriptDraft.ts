import { onMounted, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import type { SnapshotLine } from '@/js/yjs/yjsSnapshot';
import type * as Y from 'yjs';

// Module-level, not per-composable-instance: more than one component can mount this
// composable at once (e.g. an editor plus a presence panel). Without a refcount, the
// second mount's join would be ignored (fine) but the *first* unmount would tear the
// room down for both — whoever happens to unmount first kills it for every other
// consumer.
let activeConsumers = 0;

/**
 * Joins the active revision's collaborative draft room on mount and leaves it on
 * unmount (once every consumer has unmounted), exposing the store's reactive collab
 * state plus a plain-object page snapshot for read paths. Edits are written directly to
 * the live Y.Doc via `getDraftYdoc()`, not through the (read-only) snapshot returned
 * here.
 */
export function useScriptDraft() {
  const store = useScriptDraftStore();
  const {
    status,
    hasUnsentChanges,
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
    // Decide from the store's real state, not the count alone: joinScriptRoom() can
    // no-op (socket not connected) and the room can be torn down out-of-band
    // (ROOM_CLOSED, a rejected join), either of which would leave the count claiming
    // a room exists so that no later mount ever joins.
    if (!store.isDraftActive) {
      store.joinScriptRoom();
    }
  });

  onBeforeUnmount(() => {
    activeConsumers = Math.max(0, activeConsumers - 1);
    if (activeConsumers === 0) {
      store.leaveScriptRoom();
    }
  });

  function getPageSnapshot(page: number | string): readonly SnapshotLine[] {
    return store.getPageSnapshot(page);
  }

  function getDraftYdoc(): Y.Doc | null {
    return store.getDraftYdoc();
  }

  return {
    status,
    hasUnsentChanges,
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
