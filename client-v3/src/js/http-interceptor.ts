import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';

export default function setupHttpInterceptor(): void {
  const originalFetch = window.fetch;

  let isRefreshingToken = false;

  window.fetch = async (resource, options = {}) => {
    if (typeof resource === 'string' && resource.startsWith(makeURL('/api/'))) {
      // Import store inside the override function — Pinia context isn't active at module load time
      const { useUserStore } = await import('@/stores/user');
      const userStore = useUserStore();

      const token = userStore.authToken;
      const isLogoutRequest = resource.endsWith('/api/v1/auth/logout');
      const isLoginRequest = resource.endsWith('/api/v1/auth/login');
      const isRefreshRequest = resource.endsWith('/api/v1/auth/refresh-token');

      const newOptions = {
        ...options,
        headers: {
          ...options.headers,
        } as Record<string, string>,
      };

      if (token && !Object.keys(newOptions.headers).includes('Authorization')) {
        newOptions.headers = { ...newOptions.headers, Authorization: `Bearer ${token}` };
      }

      if (
        (!options.headers || !(options.headers as Record<string, string>)['Content-Type']) &&
        (options.method === 'POST' || options.method === 'PUT')
      ) {
        newOptions.headers['Content-Type'] = 'application/json';
      }

      try {
        const response = await originalFetch(resource, newOptions);

        if (response.status === 401 && !isLogoutRequest && !isLoginRequest) {
          log.warn('Received 401 Unauthorized response');

          if (isRefreshRequest || isRefreshingToken) {
            log.warn('Token refresh failed with 401 or already refreshing, logging out');
            toast.warning('Your session has expired. Please log in again.');
            await userStore.logout();
            return response;
          }

          log.info('Attempting token refresh');
          if (token) {
            try {
              isRefreshingToken = true;
              const refreshSuccess = await userStore.refreshToken();
              isRefreshingToken = false;

              if (refreshSuccess) {
                log.info('Token refresh successful, retrying original request');
                const retriedOptions = {
                  ...newOptions,
                  headers: {
                    ...newOptions.headers,
                    Authorization: `Bearer ${userStore.authToken}`,
                  },
                };
                return await originalFetch(resource, retriedOptions);
              }

              log.warn('Token refresh failed, logging out');
              toast.warning('Your session has expired. Please log in again.');
              await userStore.logout();
              return response;
            } catch (refreshError) {
              isRefreshingToken = false;
              log.error('Error during token refresh:', refreshError);
              toast.error('Authentication error - please log in again');
              await userStore.logout();
              return response;
            }
          } else {
            log.warn('401 received with no token present');
            await userStore.logout();
            return response;
          }
        }

        return response;
      } catch (error) {
        log.error('Fetch error:', error);
        throw error;
      }
    }

    return originalFetch(resource, options);
  };
}
