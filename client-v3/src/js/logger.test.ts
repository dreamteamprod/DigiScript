import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

const userState: { authToken: string | null } = { authToken: null };

vi.mock('@/stores/user', () => ({ useUserStore: () => userState }));
vi.mock('@/stores/system', () => ({
  useSystemStore: () => ({ settings: { client_log_enabled: true, client_log_level: 'DEBUG' } }),
}));

describe('remote logger', () => {
  const fetchMock = vi.fn(() => Promise.resolve(new Response('{}')));

  beforeEach(async () => {
    vi.useFakeTimers();
    vi.resetModules();
    fetchMock.mockClear();
    vi.stubGlobal('fetch', fetchMock);
    userState.authToken = null;
    const { initRemoteLogging } = await import('./logger');
    initRemoteLogging();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('holds log entries until a token exists, then sends them with it', async () => {
    const log = (await import('loglevel')).default;
    log.error('before login');
    await vi.advanceTimersByTimeAsync(2000);
    expect(fetchMock).not.toHaveBeenCalled();

    userState.authToken = 'tok';
    log.error('after login');
    await vi.advanceTimersByTimeAsync(2000);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer tok');
    const messages = JSON.parse(init.body as string).batch.map(
      (e: { message: string }) => e.message
    );
    expect(messages).toEqual(expect.arrayContaining(['before login', 'after login']));
  });

  it('keeps only the most recent 50 entries while logged out', async () => {
    const log = (await import('loglevel')).default;
    for (let i = 0; i < 80; i++) log.error(`entry ${i}`);

    userState.authToken = 'tok';
    await vi.advanceTimersByTimeAsync(2000);
    log.error('final');
    await vi.advanceTimersByTimeAsync(2000);

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    const batch = JSON.parse(init.body as string).batch as { message: string }[];
    expect(batch.length).toBeLessThanOrEqual(50);
    expect(batch.map((e) => e.message)).not.toContain('entry 0');
    expect(batch.map((e) => e.message)).toContain('final');
  });
});
