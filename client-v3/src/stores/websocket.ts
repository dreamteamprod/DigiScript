import { defineStore } from 'pinia';
import log from 'loglevel';

/** Storage key of the persisted websocket store (the plugin's default, the store id). */
export const WEBSOCKET_PERSIST_KEY = 'websocket';

/**
 * Remove the client uuid that builds before the per-tab change persisted in
 * localStorage, so that a stale shared value is never read again.
 */
export function removeLegacyPersistedUUID(): void {
  try {
    localStorage.removeItem(WEBSOCKET_PERSIST_KEY);
  } catch (e) {
    log.warn('Unable to remove legacy persisted websocket state', e);
  }
}

export const useWebSocketStore = defineStore('websocket', {
  state: () => ({
    isConnected: false,
    authenticated: false,
    authSucceeded: false,
    pendingAuthentication: false,
    internalUUID: null as string | null,
    reconnectAttempts: 0,
    // Registered by the useWebSocket composable — allows stores to send WS messages
    _sendFn: null as ((data: object) => void) | null,
  }),
  // The client uuid is per tab (sessionStorage), like the legacy client: it
  // survives a reload of the same tab, which is what REFRESH_CLIENT needs, but
  // separate tabs no longer share one server session. Older builds kept it in
  // localStorage under the same key; that copy is removed before hydrating so
  // tabs stop picking up a shared uuid from it.
  persist: {
    key: WEBSOCKET_PERSIST_KEY,
    storage: sessionStorage,
    pick: ['internalUUID'],
    beforeHydrate: () => removeLegacyPersistedUUID(),
  },
  getters: {
    websocketHealthy: (state) => state.isConnected,
  },
  actions: {
    // Called by the useWebSocket composable to register the send function
    registerSend(fn: (data: object) => void): void {
      this._sendFn = fn;
    },
    // Called after login to send auth if the WS is already connected
    triggerAuthentication(): void {
      if (!this._sendFn || !this.pendingAuthentication) return;
      const token = localStorage.getItem('digiscript_auth_token');
      if (!token) return;
      log.debug('Triggering WS authentication after login');
      this._sendFn({ OP: 'AUTHENTICATE', DATA: { token } });
    },
    // Called after token refresh to keep WS token in sync
    refreshWsToken(): void {
      if (!this._sendFn || !this.isConnected) return;
      const token = localStorage.getItem('digiscript_auth_token');
      if (!token) return;
      this._sendFn({ OP: 'REFRESH_TOKEN', DATA: { token } });
    },
  },
});
