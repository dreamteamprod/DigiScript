import store from '@/store/store';
import Vue from 'vue';
import log from 'loglevel';
import { makeURL } from '@/js/utils';

export default function setupHttpInterceptor() {
  // Store the original fetch function
  const originalFetch = window.fetch;
  
  let isRefreshingToken = false;
  
  // Replace with our enhanced version
  window.fetch = async (resource, options = {}) => {
    // Only intercept our own API requests
    if (typeof resource === 'string' && resource.startsWith(makeURL('/api/'))) {
      const token = store.getters.AUTH_TOKEN;
      const isLogoutRequest = resource.endsWith('/api/v1/auth/logout');
      const isRefreshRequest = resource.endsWith('/api/v1/auth/refresh-token');

      // Clone the options
      const newOptions = {
        ...options,
        headers: {
          ...options.headers,
        },
      };

      // Add token if it exists
      if (token) {
        newOptions.headers = {
          ...newOptions.headers,
          Authorization: `Bearer ${token}`,
        };
      }

      // Add content-type if not already set and it's a POST request
      if ((!options.headers || !options.headers['Content-Type'])
          && (options.method === 'POST' || options.method === 'PUT')) {
        newOptions.headers['Content-Type'] = 'application/json';
      }

      try {
        // Make the request with enhanced options
        const response = await originalFetch(resource, newOptions);

        // Handle 401 Unauthorized errors globally
        if (response.status === 401 && !isLogoutRequest) {
          log.warn('Received 401 Unauthorized response');
          
          if (isRefreshRequest || isRefreshingToken) {
            log.warn('Token refresh failed with 401 or already refreshing, logging out');
            Vue.$toast.warning('Your session has expired. Please log in again.');
            await store.dispatch('USER_LOGOUT');
            return response;
          }
          
          log.info('Attempting token refresh');
          
          // Try to refresh the token if we have one
          if (token) {
            try {
              isRefreshingToken = true;
              const refreshSuccess = await store.dispatch('REFRESH_TOKEN');
              isRefreshingToken = false;

              if (refreshSuccess) {
                log.info('Token refresh successful, retrying original request');
                // Retry the original request with the new token
                const retriedOptions = {
                  ...newOptions,
                  headers: {
                    ...newOptions.headers,
                    Authorization: `Bearer ${store.getters.AUTH_TOKEN}`,
                  },
                };
                return await originalFetch(resource, retriedOptions);
              }
              // If refresh fails, handle unauthorized state
              log.warn('Token refresh failed, logging out');
              Vue.$toast.warning('Your session has expired. Please log in again.');
              await store.dispatch('USER_LOGOUT');

              // Return the original 401 response
              return response;
            } catch (refreshError) {
              isRefreshingToken = false;
              log.error('Error during token refresh:', refreshError);
              Vue.$toast.error('Authentication error - please log in again');
              await store.dispatch('USER_LOGOUT');
              return response;
            }
          } else {
            // No token, just log the user out
            log.warn('401 received with no token present');
            await store.dispatch('USER_LOGOUT');
            return response;
          }
        }

        return response;
      } catch (error) {
        log.error('Fetch error:', error);
        throw error;
      }
    }

    // Pass through non-API requests
    return originalFetch(resource, options);
  };
}
