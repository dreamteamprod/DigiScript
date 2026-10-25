import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const getters: Record<string, unknown> = {};

vi.mock('@/store/store', () => ({ default: { getters, watch: vi.fn() } }));

describe('remote logger', () => {
  const fetchMock = vi.fn(() => Promise.resolve(new Response('{}')));
  let log: typeof import('loglevel').default;

  const sentBatches = () =>
    fetchMock.mock.calls.map((call) => {
      const [, init] = call as unknown as [string, RequestInit];
      return {
        auth: (init.headers as Record<string, string>).Authorization,
        messages: (JSON.parse(init.body as string).batch as { message: string }[]).map(
          (e) => e.message
        ),
      };
    });

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.resetModules();
    fetchMock.mockClear();
    vi.stubGlobal('fetch', fetchMock);
    getters.AUTH_TOKEN = null;
    getters.SETTINGS = { client_log_enabled: true, client_log_level: 'DEBUG' };
    await (await import('./logger')).initRemoteLogging();
    log = (await import('loglevel')).default;
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('does not post while logged out and flushes the held entries after login', async () => {
    log.error('queued while logged out');
    await vi.advanceTimersByTimeAsync(2000);
    expect(fetchMock).not.toHaveBeenCalled();

    getters.AUTH_TOKEN = 'tok';
    log.error('logged in');
    await vi.advanceTimersByTimeAsync(2000);

    const [batch] = sentBatches();
    expect(batch.auth).toBe('Bearer tok');
    expect(batch.messages).toEqual(
      expect.arrayContaining(['queued while logged out', 'logged in'])
    );
  });

  it('caps the logged-out queue at the 50 most recent entries', async () => {
    for (let i = 0; i < 80; i++) log.error(`entry ${i}`);
    getters.AUTH_TOKEN = 'tok';
    log.error('final');
    await vi.advanceTimersByTimeAsync(2000);

    const [batch] = sentBatches();
    expect(batch.messages.length).toBeLessThanOrEqual(50);
    expect(batch.messages).not.toContain('entry 0');
    expect(batch.messages).toContain('final');
  });
});
