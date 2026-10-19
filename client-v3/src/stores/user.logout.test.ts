import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useUserStore } from './user';
import { useWebSocketStore } from './websocket';

// An in-app logout followed by a login (no page reload) must re-authenticate the
// existing WebSocket, so the server can settle ownership (and, for a different
// user, move this tab to a fresh client id).

vi.mock('@/router', () => ({
  default: { currentRoute: { value: { path: '/' } }, push: vi.fn() },
}));
vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn(), warning: vi.fn() },
}));

describe('logout then login re-authenticates the WebSocket', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    localStorage.clear();
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({}), { status: 200 }))
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('marks the socket as waiting for authentication', async () => {
    const wsStore = useWebSocketStore();
    const send = vi.fn();
    wsStore.registerSend(send);
    // As after an earlier successful WS authentication.
    wsStore.$patch({ authenticated: true, authSucceeded: true, pendingAuthentication: false });
    const userStore = useUserStore();
    userStore._setToken('old-token');

    await userStore.logout();
    expect(wsStore.pendingAuthentication).toBe(true);

    // The next login stores a token and triggers WS authentication.
    localStorage.setItem('digiscript_auth_token', 'new-token');
    wsStore.triggerAuthentication();
    expect(send).toHaveBeenCalledWith({ OP: 'AUTHENTICATE', DATA: { token: 'new-token' } });
  });
});
