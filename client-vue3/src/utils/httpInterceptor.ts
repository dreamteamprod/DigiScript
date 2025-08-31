import { makeURL } from '@/utils/index';

export default function setupHttpInterceptor() {
  // Store the original fetch function
  const originalFetch = window.fetch;

  let isRefreshingToken = false;

  // Replace with our enhanced version
  window.fetch = async (resource: RequestInfo | URL, options: RequestInit = {}) => {
    // Only intercept our own API requests
    if (typeof resource === 'string' && resource.startsWith(makeURL('/api/'))) {
      // Get token from localStorage directly to avoid Pinia initialization issues
      const token = localStorage.getItem('digiscript_auth_token');
      const isLogoutRequest = resource.endsWith('/api/v1/auth/logout');
      const isRefreshRequest = resource.endsWith('/api/v1/auth/refresh-token');

      // Clone the options
      const newOptions: RequestInit = {
        ...options,
        headers: {
          ...options.headers,
        },
      };

      // Add token if it exists and Authorization header is not already set
      if (token && !Object.keys(newOptions.headers || {}).some((key) => key.toLowerCase() === 'authorization')) {
        newOptions.headers = {
          ...newOptions.headers,
          Authorization: `Bearer ${token}`,
        };
      }

      // Add content-type if not already set and it's a POST/PUT request
      if ((!options.headers || !Object.keys(options.headers).some((key) => key.toLowerCase() === 'content-type')) && (options.method === 'POST' || options.method === 'PUT')) {
        newOptions.headers = {
          ...newOptions.headers,
          'Content-Type': 'application/json',
        };
      }

      try {
        // Make the request with enhanced options
        const response = await originalFetch(resource, newOptions);

        // Handle 401 Unauthorized errors globally
        if (response.status === 401 && !isLogoutRequest) {
          console.warn('Received 401 Unauthorized response');

          if (isRefreshRequest || isRefreshingToken) {
            console.warn('Token refresh failed with 401 or already refreshing, logging out');
            // TODO: Add toast notification when toast system is available
            console.warn('Your session has expired. Please log in again.');
            // Clear token from localStorage
            localStorage.removeItem('digiscript_auth_token');
            return response;
          }

          console.info('Attempting token refresh');
          // Try to refresh the token if we have one
          if (token) {
            try {
              isRefreshingToken = true;

              // Try to refresh the token
              const refreshResponse = await originalFetch(makeURL('/api/v1/auth/refresh-token'), {
                method: 'POST',
                headers: {
                  'Content-Type': 'application/json',
                  Authorization: `Bearer ${token}`,
                },
              });

              isRefreshingToken = false;

              if (refreshResponse.ok) {
                const refreshData = await refreshResponse.json();
                const newToken = refreshData.access_token;

                // Update token in localStorage
                localStorage.setItem('digiscript_auth_token', newToken);

                console.info('Token refresh successful, retrying original request');
                // Retry the original request with the new token
                const retriedOptions: RequestInit = {
                  ...newOptions,
                  headers: {
                    ...newOptions.headers,
                    Authorization: `Bearer ${newToken}`,
                  },
                };
                return await originalFetch(resource, retriedOptions);
              }
              // If refresh fails, handle unauthorized state
              console.warn('Token refresh failed, logging out');
              // TODO: Add toast notification when toast system is available
              console.warn('Your session has expired. Please log in again.');

              // Clear token from localStorage
              localStorage.removeItem('digiscript_auth_token');

              // Return the original 401 response
              return response;
            } catch (refreshError) {
              isRefreshingToken = false;
              console.error('Error during token refresh:', refreshError);
              // TODO: Add toast notification when toast system is available
              console.error('Authentication error - please log in again');

              // Clear token from localStorage
              localStorage.removeItem('digiscript_auth_token');
              return response;
            }
          } else {
            // No token, just return the 401
            console.warn('401 received with no token present');
            return response;
          }
        }

        return response;
      } catch (error) {
        console.error('Fetch error:', error);
        throw error;
      }
    }

    // Pass through non-API requests
    return originalFetch(resource, options);
  };
}
