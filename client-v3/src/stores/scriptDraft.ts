import { defineStore } from 'pinia';
import * as Y from 'yjs';
import log from 'loglevel';
import { toast } from '@/js/toast';
import { useWebSocket } from '@/composables/useWebSocket';
import { useWebSocketStore } from '@/stores/websocket';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { ScriptDocProvider, SERVER_ORIGIN } from '@/js/yjs/ScriptDocProvider';
import { ydocPagesToPlain, ydocDeletedLineIds } from '@/js/yjs/yjsSnapshot';
import type { SnapshotLine } from '@/js/yjs/yjsSnapshot';
import type {
  RoomMember,
  RoomMembersMessage,
  CollabErrorMessage,
  ScriptSavedMessage,
  SaveProgressMessage,
} from '@/types/api/scriptDraft';

// The Y.Doc/provider must never live inside Pinia's reactive state — Vue 3's Proxy
// walks nested objects the same way Vue 2's defineProperty did, and Yjs's internal
// bookkeeping (_item, _map, doc, ...) breaks under that walk. A plain module-level
// holder, outside `state()` entirely, is never touched by Pinia's reactivity at all —
// nothing to opt out of. It is intentionally a singleton: the backend only ever
// supports one active draft room per app instance.
let ydoc: Y.Doc | null = null;
let provider: ScriptDocProvider | null = null;
let unsubscribeDocUpdate: (() => void) | null = null;
// Count of local-origin doc updates since the last saveDraft() call, used to decide
// whether a following scriptSaved is allowed to clear isDraftDirty (see scriptSaved).
let localEditsSinceSaveRequest = 0;

export const useScriptDraftStore = defineStore('scriptDraft', {
  state: () => ({
    isDraftActive: false,
    isDraftSynced: false,
    isDraftSaving: false,
    isDraftDirty: false,
    draftLastSavedAt: null as string | null,
    lastCollabError: null as string | null,
    members: [] as RoomMember[],
    pageSaveProgress: null as SaveProgressMessage | null,
    pageSnapshots: {} as Record<string, SnapshotLine[]>,
    deletedLineIds: [] as number[],
  }),

  getters: {
    getPageSnapshot:
      (state) =>
      (page: number | string): SnapshotLine[] =>
        state.pageSnapshots[String(page)] ?? [],

    // scriptConfig.ts owns GET_SCRIPT_CONFIG_STATUS (see the comment there), and its
    // editors/cutters are real Pinia state, so these getters track correctly. Exposed
    // here too since this is the store the plan designates as owning collab state
    // conceptually — components should read editors/cutters from here.
    editors: () => useScriptConfigStore().editors,
    cutters: () => useScriptConfigStore().cutters,
  },

  actions: {
    /**
     * The live Y.Doc, or null when no draft room is joined. A plain method, not a
     * getter: a Pinia options-store getter is a `computed()`, and `ydoc` is a plain
     * module-level variable with no reactive dependency for that computed to track —
     * it would evaluate once and cache that value forever, never seeing a later
     * join/leave. Always call this fresh rather than holding the result.
     */
    getDraftYdoc(): Y.Doc | null {
      return ydoc;
    },

    /** Join the active revision's collaborative draft room and start syncing. */
    joinScriptRoom(): void {
      if (ydoc) {
        if (this.isDraftActive) {
          log.warn('scriptDraft: joinScriptRoom called while already active, ignoring');
          return;
        }
        // A doc exists but this instance doesn't think it's active — a stale resource
        // left behind by a previous store instance (HMR, a caller that skipped
        // teardown). Clear it before allocating a new one rather than silently
        // overwriting a still-listening doc/provider.
        log.warn(
          'scriptDraft: joinScriptRoom found a stale doc with no active instance, clearing it first'
        );
        this._teardown();
      }

      if (!useWebSocketStore().isConnected) {
        toast.error('Cannot open script draft: not connected to the server');
        return;
      }

      const doc = new Y.Doc();
      ydoc = doc;
      provider = new ScriptDocProvider(doc, useWebSocket().sendObj);
      localEditsSinceSaveRequest = 0;

      // Doc-wide, not scoped to `pages` — deleted_line_ids and meta are separate
      // top-level shared types, and a `pages`-only observer would miss a change that
      // touches only one of those (e.g. a save that clears deleted_line_ids without
      // needing to ID-patch any page).
      const refreshSnapshot = (_update: Uint8Array, origin: unknown): void => {
        this.pageSnapshots = ydocPagesToPlain(doc);
        this.deletedLineIds = ydocDeletedLineIds(doc);
        this.isDraftDirty = true;
        if (origin !== SERVER_ORIGIN) {
          localEditsSinceSaveRequest += 1;
        }
      };
      doc.on('update', refreshSnapshot);
      unsubscribeDocUpdate = () => doc.off('update', refreshSnapshot);

      this.isDraftActive = true;
      this.isDraftSynced = false;
      this.isDraftDirty = false;
      this.lastCollabError = null;
      this.pageSnapshots = {};
      this.deletedLineIds = [];
      this.members = [];

      provider.join();
    },

    /** Leave the draft room and tear down the Y.Doc. Safe to call when not active. */
    leaveScriptRoom(): void {
      provider?.leave();
      this._teardown();
    },

    /** Internal teardown shared by leaveScriptRoom and the server-initiated ROOM_CLOSED. */
    _teardown(): void {
      unsubscribeDocUpdate?.();
      unsubscribeDocUpdate = null;
      provider?.destroy();
      provider = null;
      ydoc?.destroy();
      ydoc = null;
      localEditsSinceSaveRequest = 0;

      this.isDraftActive = false;
      this.isDraftSynced = false;
      this.isDraftSaving = false;
      this.isDraftDirty = false;
      this.draftLastSavedAt = null;
      this.pageSnapshots = {};
      this.deletedLineIds = [];
      this.members = [];
      this.pageSaveProgress = null;
    },

    saveDraft(): void {
      if (!this.isDraftActive) return;
      if (!useWebSocketStore().isConnected) {
        toast.error('Cannot save script draft: not connected to the server');
        return;
      }
      this.isDraftSaving = true;
      this.lastCollabError = null;
      localEditsSinceSaveRequest = 0;
      useWebSocket().sendObj({ OP: 'SAVE_SCRIPT_DRAFT', DATA: {} });
    },

    discardDraft(): void {
      if (!this.isDraftActive) return;
      if (!useWebSocketStore().isConnected) {
        toast.error('Cannot discard script draft: not connected to the server');
        return;
      }
      useWebSocket().sendObj({ OP: 'DISCARD_SCRIPT_DRAFT', DATA: {} });
    },

    // --- WS action handlers, dispatched automatically by useWebSocket's
    // ACTION → camelCase convention (see the useWebSocket composable's
    // screamingToCamel/dispatchAction). Adding a method here is sufficient; no
    // registration needed. ---

    yjsSync(data: { step: number; payload: string }): void {
      if (!provider) {
        log.warn('scriptDraft: yjsSync received with no active provider, dropping');
        return;
      }
      const applied = provider.applySync(data);
      if (data.step !== 0) return;
      if (applied) {
        this.isDraftSynced = true;
        this.isDraftDirty = false;
      } else {
        // Do not report synced over a doc that may now be empty/stale — leave
        // isDraftSynced false so callers keep showing a loading/error state rather
        // than a false "ready" one.
        this.lastCollabError = 'Failed to apply the initial script sync';
        toast.error('Failed to load the script draft — try rejoining');
      }
    },

    yjsUpdate(data: { payload: string }): void {
      if (!provider) {
        log.warn('scriptDraft: yjsUpdate received with no active provider, dropping');
        return;
      }
      provider.applyUpdate(data);
    },

    yjsAwareness(_data: { payload: string }): void {
      // Decoded and relayed by ScriptDocProvider's caller once Phase 4 wires up
      // y-protocols/awareness for CollaboratorPanel/line-level presence. Nothing to
      // do yet — accepting the action (rather than leaving it unhandled) avoids
      // "No handler for WS action" log spam whenever another client is present.
    },

    roomMembers(data: RoomMembersMessage): void {
      this.members = data.members;
    },

    roomClosed(): void {
      toast.info('Collaborative draft closed');
      this._teardown();
    },

    scriptSaved(data: ScriptSavedMessage): void {
      this.isDraftSaving = false;
      this.draftLastSavedAt = data.last_saved_at;
      this.pageSaveProgress = null;
      // Only clear dirty if no local edit landed after saveDraft() was sent — the
      // ID-patch YJS_UPDATE that precedes this message is applied with SERVER_ORIGIN
      // and doesn't count, but a genuine edit the user made while the save was in
      // flight isn't covered by *this* save and must stay flagged unsaved.
      if (localEditsSinceSaveRequest === 0) {
        this.isDraftDirty = false;
      }
    },

    saveError(data: CollabErrorMessage): void {
      this.isDraftSaving = false;
      this.pageSaveProgress = null;
      this.lastCollabError = data.error;
      toast.error(`Failed to save script draft: ${data.error}`);
    },

    saveProgress(data: SaveProgressMessage): void {
      this.pageSaveProgress = data;
    },

    collabError(data: CollabErrorMessage): void {
      this.lastCollabError = data.error;
      toast.error(data.error);
      // A COLLAB_ERROR while we're mid-join (active but never synced) means the join
      // itself was rejected (no show, no revision, live session, a Y.Doc build
      // failure) — the server will never send the YJS_SYNC that would otherwise
      // complete it, so the optimistic state from joinScriptRoom() must be unwound
      // rather than left active forever. A COLLAB_ERROR after a successful join (e.g.
      // an edit rejected for insufficient permissions) is a narrower failure and must
      // not tear down an otherwise-healthy room.
      if (this.isDraftActive && !this.isDraftSynced) {
        this._teardown();
      }
    },
  },
});
