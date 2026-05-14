import { defineStore } from 'pinia';
import log from 'loglevel';

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
  persist: {
    pick: ['internalUUID'],
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
