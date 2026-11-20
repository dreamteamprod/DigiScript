import { describe, it, expect, beforeEach } from 'vitest';
import { createApp } from 'vue';
import { createPinia, setActivePinia } from 'pinia';
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate';
import { useWebSocketStore, WEBSOCKET_PERSIST_KEY } from './websocket';

/** A fresh pinia with the persistence plugin, as main.ts sets it up. */
function freshPinia() {
  const pinia = createPinia();
  pinia.use(piniaPluginPersistedstate);
  // Plugins only run once pinia is installed in an app.
  createApp({}).use(pinia);
  setActivePinia(pinia);
  return pinia;
}

describe('websocket store persistence', () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it('persists the client uuid per tab, in sessionStorage only', () => {
    freshPinia();
    const store = useWebSocketStore();
    store.$patch({ internalUUID: 'uuid-tab-1' });

    expect(JSON.parse(sessionStorage.getItem(WEBSOCKET_PERSIST_KEY) ?? '{}')).toEqual({
      internalUUID: 'uuid-tab-1',
    });
    expect(localStorage.getItem(WEBSOCKET_PERSIST_KEY)).toBeNull();
  });

  it('restores the uuid after a reload of the same tab', () => {
    sessionStorage.setItem(WEBSOCKET_PERSIST_KEY, JSON.stringify({ internalUUID: 'uuid-kept' }));
    freshPinia();
    expect(useWebSocketStore().internalUUID).toBe('uuid-kept');
  });

  it('ignores and removes a uuid left in localStorage by older builds', () => {
    localStorage.setItem(WEBSOCKET_PERSIST_KEY, JSON.stringify({ internalUUID: 'shared-old' }));
    freshPinia();

    expect(useWebSocketStore().internalUUID).toBeNull();
    expect(localStorage.getItem(WEBSOCKET_PERSIST_KEY)).toBeNull();
  });

  it('does not persist connection state, only the uuid', () => {
    freshPinia();
    useWebSocketStore().$patch({ internalUUID: 'u', isConnected: true, authenticated: true });
    expect(Object.keys(JSON.parse(sessionStorage.getItem(WEBSOCKET_PERSIST_KEY) ?? '{}'))).toEqual([
      'internalUUID',
    ]);
  });
});
