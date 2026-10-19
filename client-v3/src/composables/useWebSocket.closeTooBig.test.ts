import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import { useWebSocket } from './useWebSocket';
import { toast } from '@/js/toast';

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

describe('close code 1009', () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    vi.useFakeTimers();
    vi.stubGlobal('WebSocket', FakeWebSocket);
    setActivePinia(createPinia());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
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
