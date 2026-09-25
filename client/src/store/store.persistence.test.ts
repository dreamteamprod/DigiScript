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
