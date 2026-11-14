import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useWebSocket } from './useWebSocket';
import { useWebSocketStore } from '@/stores/websocket';

// Client-id handshake: SET_UUID on (re)connect, REASSIGN_UUID when the server moves
// this tab to a different id (issue #1419 review round 3).

vi.mock('@/router', () => ({ default: { currentRoute: { value: { path: '/' } }, push: vi.fn() } }));
vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

class FakeWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static instances: FakeWebSocket[] = [];
  readyState = FakeWebSocket.OPEN;
  sent: { OP: string; DATA?: unknown }[] = [];
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

async function deliver(socket: FakeWebSocket, op: string, data: unknown): Promise<void> {
  socket.onmessage?.({ data: JSON.stringify({ OP: op, DATA: data }) });
  await new Promise((resolve) => setTimeout(resolve, 0));
}

describe('client id handshake', () => {
  let socket: FakeWebSocket;

  beforeEach(() => {
    vi.stubGlobal('WebSocket', FakeWebSocket);
    setActivePinia(createPinia());
    useWebSocket().connect();
    socket = FakeWebSocket.instances[0];
    socket.sent = [];
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('SET_UUID with a stored id asks the server to resume it', async () => {
    useWebSocketStore().$patch({ internalUUID: 'stored-id' });
    await deliver(socket, 'SET_UUID', 'fresh-id');
    expect(socket.sent).toContainEqual({ OP: 'REFRESH_CLIENT', DATA: 'stored-id' });
    expect(useWebSocketStore().internalUUID).toBe('stored-id');
  });

  it('REASSIGN_UUID replaces the stored id without asking to resume', async () => {
    useWebSocketStore().$patch({ internalUUID: 'someone-elses-id' });
    await deliver(socket, 'REASSIGN_UUID', 'my-new-id');
    expect(useWebSocketStore().internalUUID).toBe('my-new-id');
    expect(socket.sent.filter((m) => m.OP === 'REFRESH_CLIENT')).toEqual([]);
  });
});
