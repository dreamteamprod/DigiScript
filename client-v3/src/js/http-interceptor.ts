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

export default function setupHttpInterceptor(): void {
  const originalFetch = window.fetch;
  const refreshState = { isRefreshing: false };

  async function handle401Response(
    resource: string,
    newOptions: RequestInit & { headers: Record<string, string> },
    userStore: UserStore,
    isRefreshRequest: boolean,
    response: Response
  ): Promise<Response> {
    if (isRefreshRequest || refreshState.isRefreshing) {
      log.warn('Token refresh failed with 401 or already refreshing, logging out');
      toast.warning('Your session has expired. Please log in again.');
      await userStore.logout();
      return response;
    }

    log.info('Attempting token refresh');
    if (!userStore.authToken) {
      log.warn('401 received with no token present');
      await userStore.logout();
      return response;
    }

    try {
      refreshState.isRefreshing = true;
      const refreshSuccess = await userStore.refreshToken();
      refreshState.isRefreshing = false;

      if (!refreshSuccess) {
        log.warn('Token refresh failed, logging out');
        toast.warning('Your session has expired. Please log in again.');
        await userStore.logout();
        return response;
      }

      log.info('Token refresh successful, retrying original request');
      return await originalFetch(resource, {
        ...newOptions,
        headers: { ...newOptions.headers, Authorization: `Bearer ${userStore.authToken}` },
      });
    } catch (refreshError) {
      refreshState.isRefreshing = false;
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
    const isLogoutRequest = resource.endsWith('/api/v1/auth/logout');
    const isLoginRequest = resource.endsWith('/api/v1/auth/login');
    const isRefreshRequest = resource.endsWith('/api/v1/auth/refresh-token');

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
