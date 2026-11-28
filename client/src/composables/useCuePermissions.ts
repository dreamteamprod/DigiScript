import { computed } from 'vue';
import { useShowStore } from '@/stores/show';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';

/**
 * What the current person may do with cues.
 *
 * Live detection uses `showStore.currentSession`, which the server refreshes over
 * the websocket whenever a session starts or ends. `systemStore.currentShow`
 * is only re-fetched when the show itself is edited, so its
 * `current_session_id` would go stale while a cue page stays open.
 */
export function useCuePermissions() {
  const showStore = useShowStore();
  const systemStore = useSystemStore();
  const userStore = useUserStore();

  const isLiveSession = computed(() => showStore.currentSession != null);

  /** Ids of the cue types this person may add, edit and delete cues for. */
  const writableTypeIds = computed<Set<number>>(() => {
    if (systemStore.isAdminUser) return new Set(showStore.cueTypes.map((t) => t.id));
    const writeMask = systemStore.rbacRoles.find((r) => r.key === 'WRITE')?.value ?? 0;
    return new Set(
      (userStore.currentRbac?.cuetypes ?? [])
        .filter(([, mask]) => (mask & writeMask) !== 0)
        .map(([id]) => id)
    );
  });

  function canWriteType(typeId: number | null | undefined): boolean {
    return typeId != null && writableTypeIds.value.has(typeId);
  }

  /** May place cues of at least one type. */
  const canAddCues = computed(() =>
    showStore.cueTypes.some((t) => writableTypeIds.value.has(t.id))
  );

  return { isLiveSession, writableTypeIds, canWriteType, canAddCues };
}
