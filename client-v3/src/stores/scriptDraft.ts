import { defineStore } from 'pinia';
import { watch } from 'vue';
import * as Y from 'yjs';
import log from 'loglevel';
import { toast } from '@/js/toast';
import { useWebSocket } from '@/composables/useWebSocket';
import { useWebSocketStore } from '@/stores/websocket';
import { useScriptConfigStore } from '@/stores/scriptConfig';
import {
  ScriptDocProvider,
  SERVER_ORIGIN,
  type ServerSyncMessage,
  type YjsPayloadMessage,
} from '@/js/yjs/ScriptDocProvider';
import { ydocPageToPlain, ydocDeletedLineIds } from '@/js/yjs/yjsSnapshot';
import type { SnapshotLine } from '@/js/yjs/yjsSnapshot';
import type {
  RoomMember,
  RoomMembersMessage,
  CollabErrorMessage,
  ScriptSavedMessage,
  SaveProgressMessage,
} from '@/types/api/scriptDraft';

/**
 * Where the store is in the room lifecycle. `idle` = no room; `joining` = we asked to
 * join and are waiting for the server's initial state; `synced` = we hold the server's
 * state. One field rather than separate active/synced booleans so "synced but not
 * active" can't be represented.
 */
export type DraftStatus = 'idle' | 'joining' | 'synced';

/**
 * How long a save may go without any sign of life (SAVE_PROGRESS or the final
 * SCRIPT_SAVED/SAVE_ERROR) before we stop showing "saving" — the server never replies
 * if it never received the request, or dies mid-save, and the spinner would otherwise
 * stick forever.
 */
export const SAVE_STALL_TIMEOUT_MS = 30_000;

/**
 * How long a join may go without reaching `synced` before we give up — covers both a
 * `JOIN_SCRIPT_ROOM` the server never answers, and an initial sync that arrives but
 * fails to apply (see `yjsSync`). Without this, either leaves the spinner up forever:
 * `joinFailed` only fires on `status === 'idle'`, and `retryJoin()` is a no-op while
 * `isDraftActive` (which `'joining'` counts as) is still true.
 */
export const JOIN_STALL_TIMEOUT_MS = 15_000;

// The Y.Doc/provider must never live inside Pinia's reactive state — Vue 3's Proxy
// walks nested objects the same way Vue 2's defineProperty did, and Yjs's internal
// bookkeeping (_item, _map, doc, ...) breaks under that walk. A plain module-level
// holder, outside `state()` entirely, is never touched by Pinia's reactivity at all —
// nothing to opt out of. It is intentionally a singleton: the backend only ever
// supports one active draft room per app instance.
let ydoc: Y.Doc | null = null;
let provider: ScriptDocProvider | null = null;
let unsubscribeDoc: (() => void) | null = null;
let stopReconnectWatch: (() => void) | null = null;
let saveWatchdog: ReturnType<typeof setTimeout> | null = null;
let joinWatchdog: ReturnType<typeof setTimeout> | null = null;
// Count of local-origin doc updates since the last saveDraft() call, used to decide
// whether a following scriptSaved is allowed to clear isDraftDirty (see scriptSaved).
let localEditsSinceSaveRequest = 0;
// Whether a save *we* sent is still awaiting its SCRIPT_SAVED/SAVE_ERROR response.
// Deliberately separate from `isDraftSaving`: the save-stall watchdog resets
// `isDraftSaving` on a timeout purely so the UI (the Save button, Stop Editing)
// unsticks itself — it does not mean the request stopped being ours, and a late
// SCRIPT_SAVED for it can still arrive after that reset. Only cleared by
// scriptSaved()/saveError() actually resolving it, never by the watchdog.
let ownSaveInFlight = false;

// One shared, stable empty page so components reading a missing page don't get a fresh
// array (and a needless re-render) on every access.
const NO_LINES: readonly SnapshotLine[] = [];

export const useScriptDraftStore = defineStore('scriptDraft', {
  state: () => ({
    status: 'idle' as DraftStatus,
    isDraftSaving: false,
    isDraftDirty: false,
    // True from the first local edit that couldn't be sent (socket down) until the room
    // is rejoined — those edits exist only in this browser and will not survive that.
    hasUnsentChanges: false,
    draftLastSavedAt: null as string | null,
    lastCollabError: null as string | null,
    members: [] as RoomMember[],
    pageSaveProgress: null as SaveProgressMessage | null,
    pageSnapshots: {} as Record<string, readonly SnapshotLine[]>,
    deletedLineIds: [] as number[],
  }),

  getters: {
    isDraftActive: (state): boolean => state.status !== 'idle',
    isDraftSynced: (state): boolean => state.status === 'synced',

    getPageSnapshot:
      (state) =>
      (page: number | string): readonly SnapshotLine[] =>
        state.pageSnapshots[String(page)] ?? NO_LINES,

    // scriptConfig.ts owns GET_SCRIPT_CONFIG_STATUS (useWebSocket dispatches by action
    // name to the first matching store, so two stores can't both handle it), and its
    // editors/cutters are real Pinia state, so these getters track correctly.
    // Components should read editors/cutters from here.
    editors: () => useScriptConfigStore().editors,
    cutters: () => useScriptConfigStore().cutters,

    /**
     * The store-side half of D8's save gate: dirty and not already saving. Callers
     * must also check there are no locally-open line editors (component-local state,
     * not tracked here).
     *
     * `isDraftDirty` alone misses one real case: `yjsSync` clears it unconditionally
     * on step 0 (the initial sync), which is correct for a brand new join but wrong
     * for *resuming* a draft kept from a prior Stop Editing (D9) — that draft is
     * exactly as unsaved as when it was left. `scriptConfig.hasDraft` covers it: the
     * server sets it before this client's join even starts (the REQUEST_SCRIPT_EDIT
     * round trip's GET_SCRIPT_CONFIG_STATUS precedes JOIN_SCRIPT_ROOM — see D3), so by
     * the time yjsSync resets isDraftDirty, hasDraft is already correct.
     */
    canSaveDraft: (state): boolean =>
      (state.isDraftDirty || useScriptConfigStore().hasDraft) && !state.isDraftSaving,
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

      // Authenticated, not just connected: the server decides editor/viewer role from
      // the session at join time, and a join sent before auth completes lands as viewer.
      const wsStore = useWebSocketStore();
      if (!wsStore.isConnected || !wsStore.authenticated) {
        toast.error('Cannot open script draft: not connected to the server');
        return;
      }

      const doc = new Y.Doc();
      ydoc = doc;
      provider = new ScriptDocProvider(doc, useWebSocket().sendObj, () => this._onSendFailed());

      const pages = doc.getMap('pages') as Y.Map<Y.Array<Y.Map<unknown>>>;
      const deletedIds = doc.getArray<string>('deleted_line_ids');

      // Every doc change, whatever its origin: mark the shared draft dirty (server-origin
      // updates count too — the draft has unsaved content — and the step-0 handler
      // resets it after the initial load) and count genuine local edits for the save
      // race in scriptSaved.
      const onUpdate = (_update: Uint8Array, origin: unknown): void => {
        this.isDraftDirty = true;
        if (origin !== SERVER_ORIGIN) {
          localEditsSinceSaveRequest += 1;
        }
      };
      // Patch only the pages whose contents changed, so components watching an
      // untouched page keep a referentially-identical array and don't re-render.
      // Errors are contained: an exception escaping a Yjs observer can skip the
      // observers registered after it.
      const onPagesChanged = (events: Y.YEvent<Y.AbstractType<unknown>>[]): void => {
        try {
          const changed = new Set<string>();
          events.forEach((event) => {
            if (event.target === pages) {
              (event as Y.YMapEvent<unknown>).keysChanged.forEach((key) => changed.add(key));
            } else if (typeof event.path[0] === 'string') {
              changed.add(event.path[0]);
            }
          });
          changed.forEach((key) => {
            const page = pages.get(key);
            if (page instanceof Y.Array) {
              this.pageSnapshots[key] = ydocPageToPlain(page);
            } else {
              delete this.pageSnapshots[key];
            }
          });
        } catch (e) {
          log.error('scriptDraft: failed to refresh page snapshots', e);
        }
      };
      const onDeletedChanged = (): void => {
        try {
          this.deletedLineIds = ydocDeletedLineIds(doc);
        } catch (e) {
          log.error('scriptDraft: failed to refresh deleted line ids', e);
        }
      };
      doc.on('update', onUpdate);
      pages.observeDeep(onPagesChanged);
      deletedIds.observe(onDeletedChanged);
      unsubscribeDoc = () => {
        doc.off('update', onUpdate);
        pages.unobserveDeep(onPagesChanged);
        deletedIds.unobserve(onDeletedChanged);
      };

      // The server drops us from the room whenever the socket drops, and a reconnect
      // restores our editor flag but not our room membership — without this, every
      // later edit would be sent to a room we're no longer in and silently ignored.
      stopReconnectWatch = watch(
        () => useWebSocketStore().authenticated,
        (nowAuthenticated, wasAuthenticated) => {
          if (nowAuthenticated && !wasAuthenticated && this.isDraftActive) {
            this._rejoinAfterReconnect();
          }
        }
      );

      this.status = 'joining';
      this.isDraftDirty = false;
      this.hasUnsentChanges = false;
      this.lastCollabError = null;
      this.pageSnapshots = {};
      this.deletedLineIds = [];
      this.members = [];

      if (!provider.join()) {
        this._teardown();
        toast.error('Cannot open script draft: not connected to the server');
        return;
      }
      this._armJoinWatchdog();
    },

    /** Leave the draft room and tear down the Y.Doc. Safe to call when not active. */
    leaveScriptRoom(): void {
      provider?.leave();
      this._teardown();
    },

    /** Internal teardown shared by leaveScriptRoom and the server-initiated ROOM_CLOSED. */
    _teardown(): void {
      unsubscribeDoc?.();
      unsubscribeDoc = null;
      stopReconnectWatch?.();
      stopReconnectWatch = null;
      this._clearSaveWatchdog();
      this._clearJoinWatchdog();
      provider?.destroy();
      provider = null;
      ydoc?.destroy();
      ydoc = null;
      localEditsSinceSaveRequest = 0;
      ownSaveInFlight = false;

      this.status = 'idle';
      this.isDraftSaving = false;
      this.isDraftDirty = false;
      this.hasUnsentChanges = false;
      this.draftLastSavedAt = null;
      this.pageSnapshots = {};
      this.deletedLineIds = [];
      this.members = [];
      this.pageSaveProgress = null;
    },

    /**
     * The socket came back and re-authenticated while we hold a room the server has
     * already dropped us from. Start over from the server's state rather than
     * resyncing the old doc: if that room was closed and rebuilt from the database its
     * Yjs history is unrelated to ours, and merging two independent histories of the
     * same lines would duplicate them all.
     */
    _rejoinAfterReconnect(): void {
      const lostEdits = this.hasUnsentChanges;
      this._teardown();
      this.joinScriptRoom();
      if (lostEdits) {
        toast.error(
          'Connection was lost — edits made while offline were not saved. The script draft was reloaded from the server.'
        );
      } else {
        toast.info('Reconnected — the script draft was reloaded from the server');
      }
    },

    _onSendFailed(): void {
      if (this.hasUnsentChanges) return;
      this.hasUnsentChanges = true;
      toast.error(
        'Connection lost — edits made now are not reaching the server and will be discarded when you reconnect'
      );
    },

    _armSaveWatchdog(): void {
      this._clearSaveWatchdog();
      saveWatchdog = setTimeout(() => {
        saveWatchdog = null;
        if (!this.isDraftSaving) return;
        this.isDraftSaving = false;
        this.pageSaveProgress = null;
        this.lastCollabError = 'Saving the script draft timed out';
        toast.error('Saving the script draft timed out — check the connection and try again');
      }, SAVE_STALL_TIMEOUT_MS);
    },

    _clearSaveWatchdog(): void {
      if (saveWatchdog !== null) {
        clearTimeout(saveWatchdog);
        saveWatchdog = null;
      }
    },

    _armJoinWatchdog(): void {
      this._clearJoinWatchdog();
      joinWatchdog = setTimeout(() => {
        joinWatchdog = null;
        if (this.status !== 'joining') return;
        this.lastCollabError = 'Joining the script draft timed out';
        toast.error('Joining the script draft timed out — check the connection and try again');
        this._teardown();
      }, JOIN_STALL_TIMEOUT_MS);
    },

    _clearJoinWatchdog(): void {
      if (joinWatchdog !== null) {
        clearTimeout(joinWatchdog);
        joinWatchdog = null;
      }
    },

    /**
     * Returns whether the save actually started (the frame was sent), so a
     * caller only shows a progress UI once there is actually progress to show
     * — e.g. CollabScriptEditor.vue's saveScript() only opens SaveProgressModal
     * on `true`, instead of showing "Finished saving script." for a save that
     * never left the browser.
     */
    saveDraft(): boolean {
      if (!this.isDraftActive) return false;
      // A second request while one is in flight would race two saves of the same doc.
      if (this.isDraftSaving) return false;
      this.isDraftSaving = true;
      this.lastCollabError = null;
      localEditsSinceSaveRequest = 0;
      if (!useWebSocket().sendObj({ OP: 'SAVE_SCRIPT_DRAFT', DATA: {} })) {
        this.isDraftSaving = false;
        toast.error('Cannot save script draft: not connected to the server');
        return false;
      }
      ownSaveInFlight = true;
      this._armSaveWatchdog();
      return true;
    },

    /**
     * Always attempts the send, even while `isDraftActive` is false (e.g. a
     * rejected join, or the room already closed from under us) — the server's
     * own no-room discard branch still demotes us out of any phantom editor
     * state in that case, but only if the frame actually reaches it. The only
     * caller, `discardAndStop()`, is reachable solely from the editor UI, so
     * there is never a "nothing to discard" case to additionally guard here.
     * Returns whether the frame was actually sent, so a caller only treats the
     * discard as having happened once it has — mirrors `sendStop()`'s own
     * send-then-flag pattern in `CollabScriptEditor.vue`.
     */
    discardDraft(): boolean {
      if (!useWebSocket().sendObj({ OP: 'DISCARD_SCRIPT_DRAFT', DATA: {} })) {
        toast.error('Cannot discard script draft: not connected to the server');
        return false;
      }
      return true;
    },

    // --- WS action handlers, dispatched automatically by useWebSocket's
    // ACTION → camelCase convention (see the useWebSocket composable's
    // screamingToCamel/dispatchAction). Adding a method here is sufficient; no
    // registration needed. ---

    yjsSync(data: ServerSyncMessage): void {
      if (!provider) {
        log.warn('scriptDraft: yjsSync received with no active provider, dropping');
        return;
      }
      const applied = provider.applySync(data);
      if (!applied) {
        // Covers step 0 (initial full state) and step 2 (a resync diff): a failed apply
        // leaves the local doc missing server state, so never report synced over it,
        // and surface the failure rather than diverging silently. While still joining,
        // there is no other way out of this for the caller (retryJoin() is a no-op
        // while isDraftActive, and joinFailed only fires on 'idle') — unwind exactly as
        // collabError does for a rejected join, so the Retry alert can appear.
        this.lastCollabError = 'Failed to apply a script sync from the server';
        toast.error('Failed to load the script draft — try rejoining');
        if (this.status === 'joining') {
          this._teardown();
        }
        return;
      }
      this._clearJoinWatchdog();
      this.status = 'synced';
      if (data.step === 0) {
        this.isDraftDirty = false;
      }
    },

    yjsUpdate(data: YjsPayloadMessage): void {
      if (!provider) {
        log.warn('scriptDraft: yjsUpdate received with no active provider, dropping');
        return;
      }
      if (!provider.applyUpdate(data)) {
        // An undecodable update means our doc may now be missing another editor's
        // change, and a later save would persist that divergence.
        this.lastCollabError = 'Failed to apply an update from another editor';
        toast.error('Failed to apply an update from another editor — try rejoining');
      }
    },

    yjsAwareness(_data: YjsPayloadMessage): void {
      // Presence isn't rendered yet, so there's nothing to decode. Accepting the action
      // (rather than leaving it unhandled) avoids "No handler for WS action" log spam
      // whenever another client is present.
    },

    roomMembers(data: RoomMembersMessage): void {
      this.members = data.members;
    },

    roomClosed(): void {
      toast.info('Collaborative draft closed');
      this._teardown();
    },

    scriptSaved(data: ScriptSavedMessage): void {
      // SCRIPT_SAVED goes to every client in the room, not just the one that asked for
      // the save, so this may be another editor's save. Uses `ownSaveInFlight`, not
      // `isDraftSaving`, to tell the two apart: the save-stall watchdog resets
      // `isDraftSaving` on a timeout purely for the UI (so Save/Stop Editing unstick
      // themselves), but a save we actually sent can still genuinely complete after
      // that reset — `isDraftSaving` alone would then misread a *late* reply to our
      // own save as someone else's, and unconditionally clear isDraftDirty below,
      // losing track of an edit made during the stall window.
      const wasOurSave = ownSaveInFlight;
      this.isDraftSaving = false;
      this._clearSaveWatchdog();
      this.draftLastSavedAt = data.last_saved_at;
      this.pageSaveProgress = null;
      if (wasOurSave) ownSaveInFlight = false;
      // Our own save: only clear dirty if no local edit landed after saveDraft() was
      // sent — the ID-patch YJS_UPDATE that precedes this message is applied with
      // SERVER_ORIGIN and doesn't count, but a genuine edit made while the save was in
      // flight isn't covered by it and must stay flagged unsaved. Someone else's save:
      // the server persists the shared doc, which already holds our earlier edits
      // (they were sent as YJS_UPDATEs), so clear dirty — otherwise a collaborator who
      // typed but never pressed save would show "unsaved" forever.
      if (!wasOurSave || localEditsSinceSaveRequest === 0) {
        this.isDraftDirty = false;
        localEditsSinceSaveRequest = 0;
      }
    },

    saveError(data: CollabErrorMessage): void {
      // SAVE_ERROR, unlike SCRIPT_SAVED, is only ever sent to the client that
      // requested the save (see `save_room`'s own error handling) — always ours.
      ownSaveInFlight = false;
      this.isDraftSaving = false;
      this._clearSaveWatchdog();
      this.pageSaveProgress = null;
      this.lastCollabError = data.error;
      toast.error(`Failed to save script draft: ${data.error}`);
    },

    saveProgress(data: SaveProgressMessage): void {
      this.pageSaveProgress = data;
      // Progress is a sign of life, so restart the stall timer.
      if (this.isDraftSaving) this._armSaveWatchdog();
    },

    collabError(data: CollabErrorMessage): void {
      this.lastCollabError = data.error;
      toast.error(data.error);
      // A rejected save fails via COLLAB_ERROR, not SAVE_ERROR, for both of
      // _op_save_script_draft's own rejection paths (a live session became active, or
      // _require_editor_write_access failed) — resolve it the same way saveError()
      // does. Without this, ownSaveInFlight would stay stuck true (only
      // scriptSaved()/saveError() ever clear it) until a later SCRIPT_SAVED for a
      // *different* editor's save is wrongly read as our own, leaving isDraftDirty
      // stuck true even though our edits were already included in that save. Scoped
      // to only run when a save was actually in flight — a COLLAB_ERROR for an
      // unrelated rejection (e.g. a blocked edit) must not touch any of this.
      if (ownSaveInFlight) {
        ownSaveInFlight = false;
        this.isDraftSaving = false;
        this._clearSaveWatchdog();
        this.pageSaveProgress = null;
      }
      // A COLLAB_ERROR while we're mid-join (active but never synced) means the join
      // itself was rejected (no show, no revision, live session, a Y.Doc build
      // failure) — the server will never send the YJS_SYNC that would otherwise
      // complete it, so the optimistic state from joinScriptRoom() must be unwound
      // rather than left active forever. A COLLAB_ERROR after a successful join (e.g.
      // an edit rejected for insufficient permissions) is a narrower failure and must
      // not tear down an otherwise-healthy room.
      if (this.status === 'joining') {
        this._teardown();
      }
    },
  },
});
