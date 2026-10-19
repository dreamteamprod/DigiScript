import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import * as Y from 'yjs';
import log from 'loglevel';
import { useWebSocket } from './useWebSocket';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import { useWebSocketStore } from '@/stores/websocket';
import { bytesToBase64 } from '@/js/yjs/base64';

// The store unit tests call store actions directly, so a typo in an action name (or a
// name that collides with another store's) would leave every one of them green while the
// real server message silently went unhandled. These drive real server-shaped messages
// through useWebSocket's real ACTION → camelCase dispatch.

vi.mock('@/router', () => ({ default: { currentRoute: { value: { path: '/' } }, push: vi.fn() } }));
vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

class FakeWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static instances: FakeWebSocket[] = [];
  readyState = FakeWebSocket.OPEN;
  sent: object[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor() {
    FakeWebSocket.instances.push(this);
  }

  send(data: string): void {
    this.sent.push(JSON.parse(data));
  }
}

function fullState(mutate: (doc: Y.Doc) => void): string {
  const doc = new Y.Doc();
  doc.transact(() => mutate(doc), 'local-edit');
  return bytesToBase64(Y.encodeStateAsUpdate(doc));
}

async function deliver(socket: FakeWebSocket, action: string, data: object): Promise<void> {
  socket.onmessage?.({ data: JSON.stringify({ OP: 'NOOP', ACTION: action, DATA: data }) });
  // handleMessage is async; let its dispatch settle.
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe('collab WS actions dispatched through the real useWebSocket dispatcher', () => {
  let socket: FakeWebSocket;

  beforeEach(() => {
    vi.stubGlobal('WebSocket', FakeWebSocket);
    setActivePinia(createPinia());
    useWebSocketStore().isConnected = true;
    useWebSocketStore().authenticated = true;
    // useWebSocket keeps one module-level socket for the life of the module, so the
    // first connect() creates it and later ones are no-ops — reuse that one instance.
    useWebSocket().connect();
    socket = FakeWebSocket.instances[0];
    socket.sent = [];
    // Instantiate the store so it's registered for convention-based dispatch, exactly
    // as it would be once a component uses it.
    useScriptDraftStore();
  });

  afterEach(() => {
    useScriptDraftStore()._teardown();
    vi.unstubAllGlobals();
  });

  function join() {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    return store;
  }

  it('joining sends JOIN_SCRIPT_ROOM over the real socket', () => {
    join();
    expect(socket.sent).toContainEqual({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });
  });

  it('YJS_SYNC step 0 marks the draft synced', async () => {
    const store = join();
    await deliver(socket, 'YJS_SYNC', {
      step: 0,
      payload: fullState((d) => d.getMap('meta').set('revision_id', 4)),
    });
    expect(store.isDraftSynced).toBe(true);
    expect(store.getDraftYdoc()?.getMap('meta').get('revision_id')).toBe(4);
  });

  it('YJS_UPDATE applies to the doc without echoing back over the socket', async () => {
    const store = join();
    socket.sent = [];
    await deliver(socket, 'YJS_UPDATE', {
      payload: fullState((d) => d.getMap('meta').set('touched', true)),
    });
    expect(store.getDraftYdoc()?.getMap('meta').get('touched')).toBe(true);
    expect(socket.sent).toEqual([]);
  });

  it('YJS_AWARENESS is handled (not reported as an unhandled action)', async () => {
    join();
    const debug = vi.spyOn(log, 'debug');
    await deliver(socket, 'YJS_AWARENESS', { payload: 'AA==' });
    expect(debug).not.toHaveBeenCalledWith(expect.stringContaining('No handler for WS action'));
  });

  it('ROOM_MEMBERS updates the member list', async () => {
    const store = join();
    await deliver(socket, 'ROOM_MEMBERS', {
      members: [{ user_id: 1, username: 'tim', role: 'editor' }],
    });
    expect(store.members).toEqual([{ user_id: 1, username: 'tim', role: 'editor' }]);
  });

  it('SAVE_PROGRESS records progress', async () => {
    const store = join();
    await deliver(socket, 'SAVE_PROGRESS', { page: 1, total: 4, percent: 25 });
    expect(store.pageSaveProgress).toEqual({ page: 1, total: 4, percent: 25 });
  });

  it('SCRIPT_SAVED records the save time', async () => {
    const store = join();
    await deliver(socket, 'SCRIPT_SAVED', { last_saved_at: '2026-01-01T00:00:00Z' });
    expect(store.draftLastSavedAt).toBe('2026-01-01T00:00:00Z');
  });

  it('SAVE_ERROR records the error', async () => {
    const store = join();
    await deliver(socket, 'SAVE_ERROR', { error: 'disk full' });
    expect(store.lastCollabError).toBe('disk full');
  });

  it('COLLAB_ERROR mid-join tears the room down', async () => {
    const store = join();
    await deliver(socket, 'COLLAB_ERROR', { error: 'No active revision' });
    expect(store.lastCollabError).toBe('No active revision');
    expect(store.isDraftActive).toBe(false);
  });

  it('ROOM_CLOSED tears the room down', async () => {
    const store = join();
    await deliver(socket, 'ROOM_CLOSED', {});
    expect(store.isDraftActive).toBe(false);
    expect(store.getDraftYdoc()).toBeNull();
  });
});
