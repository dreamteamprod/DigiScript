import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
import type { useUserStore } from '@/stores/user';

type UserStore = ReturnType<typeof useUserStore>;

function buildAuthenticatedOptions(
  options: RequestInit,
  token: string | null
): RequestInit & { headers: Record<string, string> } {
  const headers = { ...(options.headers as Record<string, string>) };
  if (token && !Object.keys(headers).includes('Authorization')) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  if (!headers['Content-Type'] && (options.method === 'POST' || options.method === 'PUT')) {
    headers['Content-Type'] = 'application/json';
  }
  return { ...options, headers };
}

type QueueEntry = {
  resolve: (r: Response) => void;
  resource: string;
  options: RequestInit & { headers: Record<string, string> };
};

export default function setupHttpInterceptor(): void {
  const originalFetch = window.fetch;
  const refreshState = { isRefreshing: false, queue: [] as QueueEntry[] };

  function flushQueue(newToken: string | null): void {
    const entries = refreshState.queue.splice(0);
    entries.forEach(({ resolve, resource, options }) => {
      if (newToken) {
        originalFetch(resource, {
          ...options,
          headers: { ...options.headers, Authorization: `Bearer ${newToken}` },
        }).then(resolve);
      } else {
        resolve(new Response(JSON.stringify({ message: 'Session expired' }), { status: 401 }));
      }
    });
  }

  async function handle401Response(
    resource: string,
    newOptions: RequestInit & { headers: Record<string, string> },
    userStore: UserStore,
    isRefreshRequest: boolean,
    response: Response
  ): Promise<Response> {
    if (isRefreshRequest) {
      log.warn('Token refresh request received 401, logging out');
      flushQueue(null);
      toast.warning('Your session has expired. Please log in again.');
      await userStore.logout();
      return response;
    }

    if (refreshState.isRefreshing) {
      return new Promise<Response>((resolve) => {
        refreshState.queue.push({ resolve, resource, options: newOptions });
      });
    }

    log.info('Attempting token refresh');
    if (!userStore.authToken) {
      log.warn('401 received with no token present');
      flushQueue(null);
      await userStore.logout();
      return response;
    }

    try {
      refreshState.isRefreshing = true;
      const refreshSuccess = await userStore.refreshToken();
      refreshState.isRefreshing = false;

      if (!refreshSuccess) {
        log.warn('Token refresh failed, logging out');
        flushQueue(null);
        toast.warning('Your session has expired. Please log in again.');
        await userStore.logout();
        return response;
      }

      log.info('Token refresh successful, retrying original request');
      flushQueue(userStore.authToken);
      return await originalFetch(resource, {
        ...newOptions,
        headers: { ...newOptions.headers, Authorization: `Bearer ${userStore.authToken}` },
      });
    } catch (refreshError) {
      refreshState.isRefreshing = false;
      flushQueue(null);
      log.error('Error during token refresh:', refreshError);
      toast.error('Authentication error - please log in again');
      await userStore.logout();
      return response;
    }
  }

  window.fetch = async (resource, options = {}) => {
    if (typeof resource !== 'string' || !resource.startsWith(makeURL('/api/'))) {
      return originalFetch(resource, options);
    }

    // Import store inside the override — Pinia context isn't active at module load time
    const { useUserStore } = await import('@/stores/user');
    const userStore = useUserStore();

    const newOptions = buildAuthenticatedOptions(options, userStore.authToken);
    const isLogoutRequest = resource.includes('/api/v1/auth/logout');
    const isLoginRequest = resource.includes('/api/v1/auth/login');
    const isRefreshRequest = resource.includes('/api/v1/auth/refresh-token');

    try {
      const response = await originalFetch(resource, newOptions);

      if (response.status === 401 && !isLogoutRequest && !isLoginRequest) {
        log.warn('Received 401 Unauthorized response');
        return handle401Response(resource, newOptions, userStore, isRefreshRequest, response);
      }

      return response;
    } catch (error) {
      log.error('Fetch error:', error);
      throw error;
    }
  };
}
