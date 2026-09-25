import { describe, it, expect, beforeEach, vi } from 'vitest';

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
    store.commit('SOCKET_ONMESSAGE', { OP: 'REASSIGN_UUID', DATA: 'my-new-id' });

    expect(store.state.websocket.internalUUID).toBe('my-new-id');
    expect(store.state.websocket.newConnection).toBe(true);
    const persisted = JSON.parse(sessionStorage.getItem('digiscript') ?? '{}');
    expect(persisted.websocket.internalUUID).toBe('my-new-id');
  });
});
