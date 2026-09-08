import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import * as Y from 'yjs';
import { useScriptDraftStore } from './scriptDraft';
import { useScriptConfigStore } from './scriptConfig';
import { bytesToBase64 } from '@/js/yjs/base64';

const sendObj = vi.fn();
vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({ sendObj, connect: vi.fn() }),
}));

vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

describe('scriptDraft store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    sendObj.mockClear();
  });

  // The Y.Doc/provider live in a module-level holder (see scriptDraft.ts), shared
  // across every store instance regardless of which Pinia is active — a test that
  // joins without leaving would leak into the next one via the "already active"
  // guard, so tear down unconditionally after every test regardless of what the
  // test itself already did.
  afterEach(() => {
    useScriptDraftStore()._teardown();
  });

  it('joinScriptRoom creates a Y.Doc and sends JOIN_SCRIPT_ROOM', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    expect(store.isDraftActive).toBe(true);
    expect(store.isDraftSynced).toBe(false);
    expect(store.draftYdoc).not.toBeNull();
    expect(sendObj).toHaveBeenCalledWith({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });
  });

  it('ignores a second joinScriptRoom call while already active', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    const doc = store.draftYdoc;
    sendObj.mockClear();

    store.joinScriptRoom();

    expect(sendObj).not.toHaveBeenCalled();
    expect(store.draftYdoc).toBe(doc);
  });

  it('leaveScriptRoom sends LEAVE_SCRIPT_ROOM, destroys the doc, and resets state', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    sendObj.mockClear();

    store.leaveScriptRoom();

    expect(sendObj).toHaveBeenCalledWith({ OP: 'LEAVE_SCRIPT_ROOM', DATA: {} });
    expect(store.isDraftActive).toBe(false);
    expect(store.draftYdoc).toBeNull();
  });

  it('yjsSync step=0 applies the full state and marks the draft synced', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    const remoteDoc = new Y.Doc();
    remoteDoc.transact(() => {
      remoteDoc.getMap('meta').set('revision_id', 5);
    }, 'local-edit');
    const fullState = Y.encodeStateAsUpdate(remoteDoc);
    sendObj.mockClear();

    store.yjsSync({ step: 0, payload: bytesToBase64(fullState) });

    expect(store.isDraftSynced).toBe(true);
    expect(store.isDraftDirty).toBe(false);
    expect(store.draftYdoc?.getMap('meta').get('revision_id')).toBe(5);
    // Applying a server-originated sync must never be echoed back as a YJS_UPDATE.
    expect(sendObj).not.toHaveBeenCalled();
  });

  it('applying a remote update rebuilds the page snapshot without echoing it back', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    const remoteDoc = new Y.Doc();
    remoteDoc.transact(() => {
      const pages = remoteDoc.getMap('pages');
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
    }, 'local-edit');
    sendObj.mockClear();

    store.yjsUpdate({ payload: bytesToBase64(Y.encodeStateAsUpdate(remoteDoc)) });

    expect(store.getPageSnapshot('1')).toHaveLength(1);
    expect(store.getPageSnapshot('1')[0]._id).toBe('10');
    expect(sendObj).not.toHaveBeenCalled();
  });

  it('a genuine local edit after joining is sent as YJS_UPDATE', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    sendObj.mockClear();

    store.draftYdoc?.transact(() => {
      store.draftYdoc?.getMap('meta').set('touched', true);
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
    const remoteDoc = new Y.Doc();
    remoteDoc.transact(() => {
      const pages = remoteDoc.getMap('pages');
      const pageArr = new Y.Array<Y.Map<unknown>>();
      pages.set('1', pageArr);
      const lineMap = new Y.Map<unknown>();
      lineMap.set('_id', '501');
      lineMap.set('parts', new Y.Array());
      pageArr.push([lineMap]);
    }, 'local-edit');
    store.yjsUpdate({ payload: bytesToBase64(Y.encodeStateAsUpdate(remoteDoc)) });
    expect(store.isDraftDirty).toBe(true);

    store.scriptSaved({ last_saved_at: '2026-01-01T00:00:00Z' });

    expect(store.isDraftDirty).toBe(false);
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
    expect(store.draftYdoc).toBeNull();
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

  it('saveProgress records page/total progress', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();

    store.saveProgress({ page: 2, total: 5 });

    expect(store.pageSaveProgress).toEqual({ page: 2, total: 5 });
  });

  it('collabError records the error message', () => {
    const store = useScriptDraftStore();
    store.collabError({ error: 'insufficient permissions' });
    expect(store.lastCollabError).toBe('insufficient permissions');
  });

  it('saveDraft/discardDraft are no-ops when no draft is active', () => {
    const store = useScriptDraftStore();
    store.saveDraft();
    store.discardDraft();
    expect(sendObj).not.toHaveBeenCalled();
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
