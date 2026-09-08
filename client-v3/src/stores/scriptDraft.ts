import { defineStore } from 'pinia';
import * as Y from 'yjs';
import log from 'loglevel';
import { toast } from '@/js/toast';
import { useWebSocket } from '@/composables/useWebSocket';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import { ScriptDocProvider } from '@/js/yjs/ScriptDocProvider';
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
// bookkeeping (_item, _map, doc, ...) breaks under that walk (see plan decision #2).
// A plain module-level holder, outside `state()` entirely, is never touched by Pinia's
// reactivity at all — nothing to opt out of.
let ydoc: Y.Doc | null = null;
let provider: ScriptDocProvider | null = null;
let unsubscribeDocUpdate: (() => void) | null = null;

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
    /** The live Y.Doc, or null when no draft room is joined. Never store this — read it fresh. */
    draftYdoc: () => ydoc,

    getPageSnapshot:
      (state) =>
      (page: number | string): SnapshotLine[] =>
        state.pageSnapshots[String(page)] ?? [],

    // Owned by scriptConfig.ts (see the comment there) — exposed here too since
    // this is the store the plan designates as owning collab state conceptually.
    editors: () => useScriptConfigStore().editors,
    cutters: () => useScriptConfigStore().cutters,
  },

  actions: {
    /** Join the active revision's collaborative draft room and start syncing. */
    joinScriptRoom(): void {
      if (this.isDraftActive) {
        log.warn('scriptDraft: joinScriptRoom called while already active, ignoring');
        return;
      }

      const doc = new Y.Doc();
      ydoc = doc;
      provider = new ScriptDocProvider(doc, useWebSocket().sendObj);

      // Doc-wide, not scoped to `pages` — deleted_line_ids and meta are separate
      // top-level shared types, and a `pages`-only observer would miss a change that
      // touches only one of those (e.g. a save that clears deleted_line_ids without
      // needing to ID-patch any page).
      const refreshSnapshot = (): void => {
        this.pageSnapshots = ydocPagesToPlain(doc);
        this.deletedLineIds = ydocDeletedLineIds(doc);
        this.isDraftDirty = true;
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

      this.isDraftActive = false;
      this.isDraftSynced = false;
      this.isDraftSaving = false;
      this.isDraftDirty = false;
      this.pageSnapshots = {};
      this.deletedLineIds = [];
      this.members = [];
      this.pageSaveProgress = null;
    },

    saveDraft(): void {
      if (!this.isDraftActive) return;
      this.isDraftSaving = true;
      this.lastCollabError = null;
      useWebSocket().sendObj({ OP: 'SAVE_SCRIPT_DRAFT', DATA: {} });
    },

    discardDraft(): void {
      if (!this.isDraftActive) return;
      useWebSocket().sendObj({ OP: 'DISCARD_SCRIPT_DRAFT', DATA: {} });
    },

    // --- WS action handlers, dispatched automatically by useWebSocket's
    // ACTION → camelCase convention. Adding a method here is sufficient; no
    // registration needed. See feedback_v3_ws_dispatch memory / plan decision #7. ---

    yjsSync(data: { step: number; payload: string }): void {
      if (!provider) return;
      provider.applySync(data);
      if (data.step === 0) {
        this.isDraftSynced = true;
        this.isDraftDirty = false;
      }
    },

    yjsUpdate(data: { payload: string }): void {
      provider?.applyUpdate(data);
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
      this.isDraftDirty = false;
      this.draftLastSavedAt = data.last_saved_at;
      this.pageSaveProgress = null;
    },

    saveError(data: CollabErrorMessage): void {
      this.isDraftSaving = false;
      this.pageSaveProgress = null;
      this.lastCollabError = data.error;
      toast.error(`Failed to save script draft: ${data.error}`);
    },

    // Dispatched WS action name is SAVE_PROGRESS → saveProgress; named to match
    // exactly, per the useWebSocket convention (see feedback_v3_ws_dispatch).
    saveProgress(data: SaveProgressMessage): void {
      this.pageSaveProgress = data;
    },

    collabError(data: CollabErrorMessage): void {
      this.lastCollabError = data.error;
      toast.error(data.error);
    },
  },
});
