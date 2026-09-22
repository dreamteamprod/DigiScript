import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import * as Y from 'yjs';
import { nextTick } from 'vue';
import { useScriptDraftStore, SAVE_STALL_TIMEOUT_MS } from './scriptDraft';
import { useScriptConfigStore } from './scriptConfig';
import { useWebSocketStore } from './websocket';
import { bytesToBase64 } from '@/js/yjs/base64';
import { toast } from '@/js/toast';

const sendObj = vi.fn((_data: object) => true);
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({ sendObj, connect: vi.fn() }),
}));

vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

function makeRemoteUpdate(mutate: (doc: Y.Doc) => void): string {
  const doc = new Y.Doc();
  doc.transact(() => mutate(doc), 'local-edit');
  return bytesToBase64(Y.encodeStateAsUpdate(doc));
}

describe('scriptDraft store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    sendObj.mockClear();
    // Every action that sends a WS message bails out early when the socket isn't
    // open (see the dedicated tests for that behavior below) — default to connected
    // so the rest of the suite exercises the normal path.
    useWebSocketStore().isConnected = true;
    useWebSocketStore().authenticated = true;
  });

  // The Y.Doc/provider live in a module-level holder (see scriptDraft.ts), shared
  // across every store instance regardless of which Pinia is active — a test that
  // joins without leaving would leak into the next one via the "already active"
  // guard, so tear down unconditionally after every test regardless of what the
  // test itself already did.
  afterEach(() => {
    vi.useRealTimers();
    useScriptDraftStore()._teardown();
  });

  it('joinScriptRoom creates a Y.Doc and sends JOIN_SCRIPT_ROOM', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    expect(store.isDraftActive).toBe(true);
    expect(store.isDraftSynced).toBe(false);
    expect(store.getDraftYdoc()).not.toBeNull();
    expect(sendObj).toHaveBeenCalledWith({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });
  });

  it('does not join when the WS is not connected', () => {
    useWebSocketStore().isConnected = false;
    const store = useScriptDraftStore();

    store.joinScriptRoom();

    expect(store.isDraftActive).toBe(false);
    expect(store.getDraftYdoc()).toBeNull();
    expect(sendObj).not.toHaveBeenCalled();
  });

  it('ignores a second joinScriptRoom call while already active', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    const doc = store.getDraftYdoc();
    sendObj.mockClear();

    store.joinScriptRoom();

    expect(sendObj).not.toHaveBeenCalled();
    expect(store.getDraftYdoc()).toBe(doc);
  });

  it('tears down and rejoins if a doc exists but this instance is not marked active (stale-resource recovery)', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    const firstDoc = store.getDraftYdoc();
    // Simulate a second store instance (a fresh Pinia — e.g. HMR) whose own
    // isDraftActive starts false even though the module-level doc is still live.
    setActivePinia(createPinia());
    useWebSocketStore().isConnected = true;
    useWebSocketStore().authenticated = true;
    const freshInstanceStore = useScriptDraftStore();
    sendObj.mockClear();

    expect(freshInstanceStore.isDraftActive).toBe(false);
    freshInstanceStore.joinScriptRoom();

    expect(freshInstanceStore.getDraftYdoc()).not.toBeNull();
    expect(freshInstanceStore.getDraftYdoc()).not.toBe(firstDoc);
    expect(firstDoc?.isDestroyed).toBe(true);
    expect(sendObj).toHaveBeenCalledWith({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });
  });

  it('leaveScriptRoom sends LEAVE_SCRIPT_ROOM, destroys the doc, and resets state', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    sendObj.mockClear();

    store.leaveScriptRoom();

    expect(sendObj).toHaveBeenCalledWith({ OP: 'LEAVE_SCRIPT_ROOM', DATA: {} });
    expect(store.isDraftActive).toBe(false);
    expect(store.getDraftYdoc()).toBeNull();
    expect(store.draftLastSavedAt).toBeNull();
  });

  it('yjsSync step=0 applies the full state and marks the draft synced', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    const payload = makeRemoteUpdate((doc) => doc.getMap('meta').set('revision_id', 5));
    sendObj.mockClear();

    store.yjsSync({ step: 0, payload });

    expect(store.isDraftSynced).toBe(true);
    expect(store.isDraftDirty).toBe(false);
    expect(store.getDraftYdoc()?.getMap('meta').get('revision_id')).toBe(5);
    // Applying a server-originated sync must never be echoed back as a YJS_UPDATE.
    expect(sendObj).not.toHaveBeenCalled();
  });

  it('yjsSync step=0 with a corrupt payload does not mark the draft synced', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    store.yjsSync({ step: 0, payload: 'not-valid-base64!!' });

    expect(store.isDraftSynced).toBe(false);
    expect(store.lastCollabError).not.toBeNull();
  });

  it('yjsSync/yjsUpdate are no-ops (and do not throw) with no active provider', () => {
    const store = useScriptDraftStore();

    expect(() => store.yjsSync({ step: 0, payload: 'x' })).not.toThrow();
    expect(() => store.yjsUpdate({ payload: 'x' })).not.toThrow();
    expect(store.isDraftSynced).toBe(false);
  });

  it('applying a remote update rebuilds the page snapshot without echoing it back', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    const payload = makeRemoteUpdate((doc) => {
      const pages = doc.getMap('pages');
      const pageArr = new Y.Array<Y.Map<unknown>>();
      pages.set('1', pageArr);
      const lineMap = new Y.Map<unknown>();
      lineMap.set('_id', '10');
      lineMap.set('act_id', 1);
      lineMap.set('scene_id', 1);
      lineMap.set('line_type', 1);
      lineMap.set('stage_direction_style_id', 0);
      lineMap.set('parts', new Y.Array());
      pageArr.push([lineMap]);
    });
    sendObj.mockClear();

    store.yjsUpdate({ payload });

    expect(store.getPageSnapshot('1')).toHaveLength(1);
    expect(store.getPageSnapshot('1')[0]._id).toBe('10');
    expect(sendObj).not.toHaveBeenCalled();
  });

  it('a remote update that only touches deleted_line_ids still refreshes deletedLineIds (pins the doc-wide listener, not a pages-scoped one)', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    const payload = makeRemoteUpdate((doc) => {
      doc.getArray<string>('deleted_line_ids').push(['77']);
    });
    sendObj.mockClear();

    store.yjsUpdate({ payload });

    expect(store.deletedLineIds).toEqual([77]);
    expect(store.getPageSnapshot('1')).toEqual([]);
  });

  it('a genuine local edit after joining is sent as YJS_UPDATE', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    sendObj.mockClear();

    store.getDraftYdoc()?.transact(() => {
      store.getDraftYdoc()?.getMap('meta').set('touched', true);
    }, 'local-edit');

    expect(sendObj).toHaveBeenCalledWith(expect.objectContaining({ OP: 'YJS_UPDATE' }));
  });

  it('ends up not-dirty after a save, even though the ID-patch YJS_UPDATE that precedes SCRIPT_SAVED marks the doc dirty in between', () => {
    // save_room sends the ID-patch as a YJS_UPDATE *before* SCRIPT_SAVED (see
    // script_room_manager.py's save_room: the ID-patch broadcast loop runs before the
    // "Notify all clients of successful save" loop, and per-connection WS delivery is
    // ordered) — so yjsUpdate flipping isDraftDirty back to true is expected to always
    // be overwritten by the scriptSaved that follows it, never the other way round.
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.saveDraft();

    // Mirror the real ID-patch shape: it rewrites a line's `_id` inside `pages`,
    // which is exactly the container refreshSnapshot's observer watches — a change
    // anywhere else (e.g. `meta`) wouldn't exercise this at all.
    const payload = makeRemoteUpdate((doc) => {
      const pages = doc.getMap('pages');
      const pageArr = new Y.Array<Y.Map<unknown>>();
      pages.set('1', pageArr);
      const lineMap = new Y.Map<unknown>();
      lineMap.set('_id', '501');
      lineMap.set('parts', new Y.Array());
      pageArr.push([lineMap]);
    });
    store.yjsUpdate({ payload });
    expect(store.isDraftDirty).toBe(true);

    store.scriptSaved({ last_saved_at: '2026-01-01T00:00:00Z' });

    expect(store.isDraftDirty).toBe(false);
  });

  it('keeps isDraftDirty true if a genuine local edit lands after saveDraft() but before scriptSaved arrives', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.saveDraft();

    // A real user edit, not a server-applied one — origin is 'local-edit', not
    // SERVER_ORIGIN, so it must count against the pending save.
    store.getDraftYdoc()?.transact(() => {
      store.getDraftYdoc()?.getMap('meta').set('typed_more', true);
    }, 'local-edit');
    expect(store.isDraftDirty).toBe(true);

    store.scriptSaved({ last_saved_at: '2026-01-01T00:00:00Z' });

    // This save's response doesn't cover the edit made after it was requested —
    // clearing isDraftDirty here would silently hide unsaved work.
    expect(store.isDraftDirty).toBe(true);
  });

  it('clears dirty on another editor\'s save — a collaborator who never pressed save is not "unsaved" forever', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    // Our own local edit, sent to the server as a YJS_UPDATE.
    store.getDraftYdoc()?.transact(() => {
      store.getDraftYdoc()?.getMap('meta').set('typed', true);
    }, 'local-edit');
    expect(store.isDraftDirty).toBe(true);
    expect(store.isDraftSaving).toBe(false);

    // SCRIPT_SAVED is broadcast to the whole room; this client didn't ask for it.
    store.scriptSaved({ last_saved_at: '2026-01-01T00:00:00Z' });

    expect(store.isDraftDirty).toBe(false);
    expect(store.draftLastSavedAt).toBe('2026-01-01T00:00:00Z');
  });

  it('a later save by us is not blocked by edits counted before the last cleared save', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.getDraftYdoc()?.transact(() => {
      store.getDraftYdoc()?.getMap('meta').set('a', 1);
    }, 'local-edit');
    store.scriptSaved({ last_saved_at: 't1' }); // someone else's save clears it

    store.saveDraft();
    store.scriptSaved({ last_saved_at: 't2' });

    expect(store.isDraftDirty).toBe(false);
  });

  it('a corrupt YJS_UPDATE surfaces an error and a toast instead of diverging silently', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    store.yjsUpdate({ payload: 'not-valid-base64!!' });

    expect(store.lastCollabError).not.toBeNull();
    expect(toast.error).toHaveBeenCalled();
  });

  it('a step=2 sync applies, marks synced, but does not reset dirty', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.getDraftYdoc()?.transact(() => {
      store.getDraftYdoc()?.getMap('meta').set('local', true);
    }, 'local-edit');
    expect(store.isDraftDirty).toBe(true);

    const payload = makeRemoteUpdate((doc) => doc.getMap('meta').set('revision_id', 3));
    store.yjsSync({ step: 2, payload });

    expect(store.isDraftSynced).toBe(true);
    expect(store.isDraftDirty).toBe(true);
    expect(store.getDraftYdoc()?.getMap('meta').get('revision_id')).toBe(3);
  });

  it('a corrupt step=2 sync does not mark synced and surfaces an error', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    store.yjsSync({ step: 2, payload: 'not-valid-base64!!' });

    expect(store.isDraftSynced).toBe(false);
    expect(store.lastCollabError).not.toBeNull();
    expect(toast.error).toHaveBeenCalled();
  });

  it('a corrupt step=0 sync shows a toast as well as recording the error', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    store.yjsSync({ step: 0, payload: 'not-valid-base64!!' });

    expect(toast.error).toHaveBeenCalled();
  });

  it('saveDraft sends SAVE_SCRIPT_DRAFT and marks the draft saving', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    sendObj.mockClear();

    store.saveDraft();

    expect(sendObj).toHaveBeenCalledWith({ OP: 'SAVE_SCRIPT_DRAFT', DATA: {} });
    expect(store.isDraftSaving).toBe(true);
  });

  it('discardDraft sends DISCARD_SCRIPT_DRAFT', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    sendObj.mockClear();

    store.discardDraft();

    expect(sendObj).toHaveBeenCalledWith({ OP: 'DISCARD_SCRIPT_DRAFT', DATA: {} });
  });

  it('saveError retried: a second saveDraft after a failed one sends again', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.saveDraft();
    store.saveError({ error: 'disk full' });
    sendObj.mockClear();

    store.saveDraft();

    expect(sendObj).toHaveBeenCalledWith({ OP: 'SAVE_SCRIPT_DRAFT', DATA: {} });
    expect(store.isDraftSaving).toBe(true);
    expect(store.lastCollabError).toBeNull();
  });

  it('roomMembers stores the member list', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    store.roomMembers({ members: [{ user_id: 1, username: 'tim', role: 'editor' }] });

    expect(store.members).toHaveLength(1);
    expect(store.members[0].username).toBe('tim');
  });

  it('roomClosed tears the room down', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    store.roomClosed();

    expect(store.isDraftActive).toBe(false);
    expect(store.getDraftYdoc()).toBeNull();
  });

  it('scriptSaved clears saving/dirty flags and records the timestamp', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.saveDraft();
    expect(store.isDraftSaving).toBe(true);

    store.scriptSaved({ last_saved_at: '2026-01-01T00:00:00Z' });

    expect(store.isDraftSaving).toBe(false);
    expect(store.isDraftDirty).toBe(false);
    expect(store.draftLastSavedAt).toBe('2026-01-01T00:00:00Z');
  });

  it('saveError clears saving and records the error', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.saveDraft();

    store.saveError({ error: 'disk full' });

    expect(store.isDraftSaving).toBe(false);
    expect(store.lastCollabError).toBe('disk full');
  });

  it('saveProgress records page/total/percent progress', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    store.saveProgress({ page: 2, total: 5, percent: 40 });

    expect(store.pageSaveProgress).toEqual({ page: 2, total: 5, percent: 40 });
  });

  it('collabError after a successful sync records the error but does not tear the room down', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.yjsSync({ step: 0, payload: makeRemoteUpdate(() => {}) });
    expect(store.isDraftSynced).toBe(true);

    store.collabError({ error: 'insufficient permissions' });

    expect(store.lastCollabError).toBe('insufficient permissions');
    expect(store.isDraftActive).toBe(true);
    expect(store.getDraftYdoc()).not.toBeNull();
  });

  it('collabError while mid-join (active but never synced) tears the room down', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    expect(store.isDraftActive).toBe(true);
    expect(store.isDraftSynced).toBe(false);

    store.collabError({ error: 'No active revision' });

    expect(store.lastCollabError).toBe('No active revision');
    expect(store.isDraftActive).toBe(false);
    expect(store.getDraftYdoc()).toBeNull();
  });

  it('collabError with no active join just records the error', () => {
    const store = useScriptDraftStore();
    store.collabError({ error: 'insufficient permissions' });
    expect(store.lastCollabError).toBe('insufficient permissions');
    expect(store.isDraftActive).toBe(false);
  });

  it('saveDraft/discardDraft are no-ops when no draft is active', () => {
    const store = useScriptDraftStore();
    store.saveDraft();
    store.discardDraft();
    expect(sendObj).not.toHaveBeenCalled();
  });

  it('does not join before the socket has authenticated (a pre-auth join would land as viewer)', () => {
    useWebSocketStore().authenticated = false;
    const store = useScriptDraftStore();

    store.joinScriptRoom();

    expect(store.isDraftActive).toBe(false);
    expect(sendObj).not.toHaveBeenCalled();
    expect(toast.error).toHaveBeenCalled();
  });

  it('unwinds the join if the JOIN_SCRIPT_ROOM frame could not be sent', () => {
    sendObj.mockReturnValueOnce(false);
    const store = useScriptDraftStore();

    store.joinScriptRoom();

    expect(store.isDraftActive).toBe(false);
    expect(store.getDraftYdoc()).toBeNull();
    expect(toast.error).toHaveBeenCalled();
  });

  it('saveDraft does not stick on "saving" when the frame could not be sent', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    sendObj.mockReturnValueOnce(false);

    store.saveDraft();

    expect(store.isDraftSaving).toBe(false);
    expect(toast.error).toHaveBeenCalled();
  });

  it('discardDraft tells the user when the frame could not be sent', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    sendObj.mockReturnValueOnce(false);

    store.discardDraft();

    expect(toast.error).toHaveBeenCalled();
  });

  it('ignores a second saveDraft while one is already in flight', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    sendObj.mockClear();

    store.saveDraft();
    store.saveDraft();

    const saves = sendObj.mock.calls.filter(
      ([m]) => (m as { OP: string }).OP === 'SAVE_SCRIPT_DRAFT'
    );
    expect(saves).toHaveLength(1);
  });

  it('stops showing "saving" when the server never replies (stall watchdog)', () => {
    vi.useFakeTimers();
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.saveDraft();

    vi.advanceTimersByTime(SAVE_STALL_TIMEOUT_MS + 1);

    expect(store.isDraftSaving).toBe(false);
    expect(store.lastCollabError).not.toBeNull();
    expect(toast.error).toHaveBeenCalled();
  });

  it('save progress counts as a sign of life and restarts the stall timer', () => {
    vi.useFakeTimers();
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.saveDraft();

    vi.advanceTimersByTime(SAVE_STALL_TIMEOUT_MS - 1000);
    store.saveProgress({ page: 1, total: 4, percent: 25 });
    vi.advanceTimersByTime(SAVE_STALL_TIMEOUT_MS - 1000);
    expect(store.isDraftSaving).toBe(true);

    vi.advanceTimersByTime(2000);
    expect(store.isDraftSaving).toBe(false);
  });

  it('a completed save cancels the stall watchdog', () => {
    vi.useFakeTimers();
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    store.saveDraft();
    store.scriptSaved({ last_saved_at: 't' });

    vi.advanceTimersByTime(SAVE_STALL_TIMEOUT_MS * 2);

    expect(store.lastCollabError).toBeNull();
    expect(toast.error).not.toHaveBeenCalled();
  });

  it('accepts a YJS_UPDATE before the initial sync without reporting synced', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    store.yjsUpdate({ payload: makeRemoteUpdate((doc) => doc.getMap('meta').set('early', 1)) });

    expect(store.getDraftYdoc()?.getMap('meta').get('early')).toBe(1);
    expect(store.isDraftSynced).toBe(false);
    expect(store.status).toBe('joining');
  });

  describe('reconnect', () => {
    async function reconnect(): Promise<void> {
      const ws = useWebSocketStore();
      ws.authenticated = false;
      await nextTick();
      ws.authenticated = true;
      await nextTick();
    }

    it('rejoins from scratch when the socket re-authenticates while a room is held', async () => {
      const store = useScriptDraftStore();
      store.joinScriptRoom();
      store.yjsSync({ step: 0, payload: makeRemoteUpdate(() => {}) });
      const firstDoc = store.getDraftYdoc();
      sendObj.mockClear();

      await reconnect();

      // A fresh doc, not a merge into the old one: if the server rebuilt the room from
      // the database its Yjs history is unrelated and merging would duplicate every line.
      expect(store.getDraftYdoc()).not.toBe(firstDoc);
      expect(firstDoc?.isDestroyed).toBe(true);
      expect(store.status).toBe('joining');
      expect(sendObj).toHaveBeenCalledWith({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });
      expect(toast.info).toHaveBeenCalled();
    });

    it('warns that offline edits were lost when local edits could not be sent', async () => {
      const store = useScriptDraftStore();
      store.joinScriptRoom();
      store.yjsSync({ step: 0, payload: makeRemoteUpdate(() => {}) });

      sendObj.mockReturnValue(false);
      store.getDraftYdoc()?.transact(() => {
        store.getDraftYdoc()?.getMap('meta').set('offline', true);
      }, 'local-edit');
      expect(store.hasUnsentChanges).toBe(true);
      sendObj.mockReturnValue(true);
      vi.mocked(toast.error).mockClear();

      await reconnect();

      expect(toast.error).toHaveBeenCalledTimes(1);
      expect(store.hasUnsentChanges).toBe(false);
    });

    it('only warns once about unsent edits, not once per keystroke', () => {
      const store = useScriptDraftStore();
      store.joinScriptRoom();
      sendObj.mockReturnValue(false);

      for (let i = 0; i < 5; i += 1) {
        store.getDraftYdoc()?.transact(() => {
          store.getDraftYdoc()?.getMap('meta').set(`k${i}`, i);
        }, 'local-edit');
      }
      sendObj.mockReturnValue(true);

      expect(vi.mocked(toast.error).mock.calls).toHaveLength(1);
    });

    it('does nothing on re-authentication when no room is held', async () => {
      const store = useScriptDraftStore();
      sendObj.mockClear();

      await reconnect();

      expect(store.isDraftActive).toBe(false);
      expect(sendObj).not.toHaveBeenCalled();
    });

    it('stops watching for reconnects once the room is left', async () => {
      const store = useScriptDraftStore();
      store.joinScriptRoom();
      store.leaveScriptRoom();
      sendObj.mockClear();

      await reconnect();

      expect(sendObj).not.toHaveBeenCalled();
    });
  });

  describe('page snapshot patching', () => {
    function addLine(doc: Y.Doc, page: string, id: string, text: string): void {
      const pages = doc.getMap('pages');
      let arr = pages.get(page) as Y.Array<Y.Map<unknown>> | undefined;
      if (!arr) {
        arr = new Y.Array<Y.Map<unknown>>();
        pages.set(page, arr);
      }
      const line = new Y.Map<unknown>();
      arr.push([line]);
      line.set('_id', id);
      line.set('act_id', 1);
      line.set('scene_id', 1);
      line.set('line_type', 1);
      line.set('stage_direction_style_id', 0);
      const parts = new Y.Array<Y.Map<unknown>>();
      line.set('parts', parts);
      const part = new Y.Map<unknown>();
      parts.push([part]);
      part.set('_id', `${id}0`);
      part.set('part_index', 0);
      part.set('character_id', 0);
      part.set('character_group_id', 0);
      part.set('line_text', new Y.Text(text));
    }

    it('leaves the snapshot of an untouched page referentially unchanged', () => {
      const store = useScriptDraftStore();
      store.joinScriptRoom();

      const remote = new Y.Doc();
      remote.transact(() => {
        addLine(remote, '1', '1', 'one');
        addLine(remote, '2', '2', 'two');
      }, 'local-edit');
      store.yjsUpdate({ payload: bytesToBase64(Y.encodeStateAsUpdate(remote)) });
      const pageTwoBefore = store.pageSnapshots['2'];
      const before = Y.encodeStateVector(remote);

      remote.transact(() => {
        const page1 = remote.getMap('pages').get('1') as Y.Array<Y.Map<unknown>>;
        const parts = page1.get(0).get('parts') as Y.Array<Y.Map<unknown>>;
        (parts.get(0).get('line_text') as Y.Text).insert(3, '!');
      }, 'local-edit');
      store.yjsUpdate({ payload: bytesToBase64(Y.encodeStateAsUpdate(remote, before)) });

      expect(store.pageSnapshots['1'][0].parts[0].line_text).toBe('one!');
      expect(store.pageSnapshots['2']).toBe(pageTwoBefore);
    });

    it('drops the snapshot of a page that no longer exists', () => {
      const store = useScriptDraftStore();
      store.joinScriptRoom();
      const remote = new Y.Doc();
      remote.transact(() => addLine(remote, '3', '9', 'x'), 'local-edit');
      store.yjsUpdate({ payload: bytesToBase64(Y.encodeStateAsUpdate(remote)) });
      expect(store.pageSnapshots['3']).toHaveLength(1);
      const before = Y.encodeStateVector(remote);

      remote.transact(() => remote.getMap('pages').delete('3'), 'local-edit');
      store.yjsUpdate({ payload: bytesToBase64(Y.encodeStateAsUpdate(remote, before)) });

      expect(store.pageSnapshots['3']).toBeUndefined();
    });

    it('a corrupt line is skipped without breaking the rest of the page', () => {
      const store = useScriptDraftStore();
      store.joinScriptRoom();
      const remote = new Y.Doc();
      remote.transact(() => {
        addLine(remote, '1', '1', 'ok');
        (remote.getMap('pages').get('1') as Y.Array<Y.Map<unknown>>).push([new Y.Map<unknown>()]);
      }, 'local-edit');

      store.yjsUpdate({ payload: bytesToBase64(Y.encodeStateAsUpdate(remote)) });

      expect(store.pageSnapshots['1'].map((l) => l._id)).toEqual(['1']);
    });
  });

  it('editors/cutters getters read from the scriptConfig store', () => {
    const store = useScriptDraftStore();
    const configStore = useScriptConfigStore();
    configStore.editors = [{ internal_id: 'abc', username: 'tim' }];
    configStore.cutters = [{ internal_id: 'def', username: 'sam' }];

    expect(store.editors).toEqual([{ internal_id: 'abc', username: 'tim' }]);
    expect(store.cutters).toEqual([{ internal_id: 'def', username: 'sam' }]);
  });
});
