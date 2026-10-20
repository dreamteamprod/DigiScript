import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Close code 1009 (message too big) must back off instead of reconnecting at the minimum
// delay forever.

vi.mock('@/router', () => ({ default: { currentRoute: { value: { path: '/' } }, push: vi.fn() } }));
vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

class FakeWebSocket {
  static OPEN = 1;
  static CONNECTING = 0;
  static instances: FakeWebSocket[] = [];
  readyState = 3;
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: ((e?: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;

  constructor() {
    FakeWebSocket.instances.push(this);
  }

  send(): void {}
}

// The composable keeps its backoff state at module level, so load a fresh copy per test.
let useWebSocket: typeof import('./useWebSocket').useWebSocket;
let toast: typeof import('@/js/toast').toast;

describe('close code 1009', () => {
  beforeEach(async () => {
    vi.resetModules();
    FakeWebSocket.instances = [];
    vi.useFakeTimers();
    vi.stubGlobal('WebSocket', FakeWebSocket);
    const { createPinia, setActivePinia } = await import('pinia');
    setActivePinia(createPinia());
    ({ useWebSocket } = await import('./useWebSocket'));
    ({ toast } = await import('@/js/toast'));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('keeps backing off when authentication succeeds between closes', async () => {
    useWebSocket().connect();
    FakeWebSocket.instances[0].onclose?.({ code: 1009 });
    vi.advanceTimersByTime(2100);
    expect(FakeWebSocket.instances).toHaveLength(2);

    // Reconnect and re-authenticate (this resets the generic error counter).
    FakeWebSocket.instances[1].onmessage?.({ data: JSON.stringify({ OP: 'WS_AUTH_SUCCESS' }) });
    await vi.advanceTimersByTimeAsync(0);
    FakeWebSocket.instances[1].onclose?.({ code: 1009 });

    // Delay must have doubled to 4s rather than starting over at 2s.
    vi.advanceTimersByTime(3500);
    expect(FakeWebSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(600);
    expect(FakeWebSocket.instances).toHaveLength(3);
    expect(toast.error).toHaveBeenCalledTimes(1);
  });

  it('reconnects even if showing the toast throws', () => {
    vi.mocked(toast.error).mockImplementationOnce(() => {
      throw new Error('toast failed');
    });
    useWebSocket().connect();
    FakeWebSocket.instances[0].onclose?.({ code: 1009 });
    vi.advanceTimersByTime(2100);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it('does not back off or notify on a normal close', () => {
    useWebSocket().connect();
    FakeWebSocket.instances[0].onclose?.({ code: 1000 });
    expect(toast.error).not.toHaveBeenCalled();
    vi.advanceTimersByTime(1100);
    expect(FakeWebSocket.instances).toHaveLength(2);
  });

  it('notifies the user once and backs off between reconnects', () => {
    useWebSocket().connect();
    FakeWebSocket.instances[0].onclose?.({ code: 1009 });
    expect(toast.error).toHaveBeenCalledTimes(1);

    // First reconnect delay is 2s (1s * 2^1): nothing after 1.5s, a new socket after 2s.
    vi.advanceTimersByTime(1500);
    expect(FakeWebSocket.instances).toHaveLength(1);
    vi.advanceTimersByTime(600);
    expect(FakeWebSocket.instances).toHaveLength(2);

    FakeWebSocket.instances[1].onclose?.({ code: 1009 });
    expect(toast.error).toHaveBeenCalledTimes(1);
    // Second delay doubles to 4s.
    vi.advanceTimersByTime(3500);
    expect(FakeWebSocket.instances).toHaveLength(2);
    vi.advanceTimersByTime(600);
    expect(FakeWebSocket.instances).toHaveLength(3);
  });
});
