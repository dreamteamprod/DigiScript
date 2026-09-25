import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('store persistence', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.resetModules();
  });

  it('keeps the client uuid per tab, in sessionStorage only', async () => {
    const { default: store } = await import('./store');
    store.commit('SOCKET_ONMESSAGE', { OP: 'SET_UUID', DATA: 'uuid-tab-1' });

    const persisted = JSON.parse(sessionStorage.getItem('digiscript') ?? '{}');
    expect(persisted.websocket.internalUUID).toBe('uuid-tab-1');
    const everywhereElse = Object.keys(localStorage).map((k) => localStorage.getItem(k));
    expect(everywhereElse.join('')).not.toContain('uuid-tab-1');
  });
});

describe('client id handshake', () => {
  beforeEach(() => {
    sessionStorage.clear();
    vi.resetModules();
  });

  it('REASSIGN_UUID replaces the stored id and marks a new connection', async () => {
    const { default: store } = await import('./store');
    store.commit('SOCKET_ONMESSAGE', { OP: 'SET_UUID', DATA: 'someone-elses-id' });
    // Seeding a fresh store already sets newConnection; clear it so the assertion
    // below measures REASSIGN_UUID itself.
    store.commit('CLEAR_NEW_CONNECTION');
    expect(store.state.websocket.newConnection).toBe(false);
    store.commit('SOCKET_ONMESSAGE', { OP: 'REASSIGN_UUID', DATA: 'my-new-id' });

    expect(store.state.websocket.internalUUID).toBe('my-new-id');
    expect(store.state.websocket.newConnection).toBe(true);
    const persisted = JSON.parse(sessionStorage.getItem('digiscript') ?? '{}');
    expect(persisted.websocket.internalUUID).toBe('my-new-id');
  });
});

describe('in-app login re-authenticates the open WebSocket', () => {
  beforeEach(() => {
    sessionStorage.clear();
    localStorage.clear();
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sends AUTHENTICATE on login after a logout, with no page reload', async () => {
    const { default: Vue } = await import('vue');
    const { default: store } = await import('./store');
    const sendObj = vi.fn();
    (Vue as unknown as { $toast: unknown }).$toast = {
      success: vi.fn(),
      error: vi.fn(),
      warning: vi.fn(),
      info: vi.fn(),
    };
    (Vue.prototype as unknown as { $socket: unknown }).$socket = {
      readyState: WebSocket.OPEN,
      sendObj,
    };
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () => new Response(JSON.stringify({ access_token: 'new-token' }), { status: 200 })
      )
    );

    await store.dispatch('USER_LOGOUT');
    expect(store.state.websocket.pendingAuthentication).toBe(true);
    sendObj.mockClear();

    await store.dispatch('USER_LOGIN', { username: 'b', password: 'pw' });
    expect(sendObj).toHaveBeenCalledWith({ OP: 'AUTHENTICATE', DATA: { token: 'new-token' } });
    await store.dispatch('USER_LOGOUT');
  });
});
