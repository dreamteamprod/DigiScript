/**
 * Electron Platform Implementation
 *
 * Provides URL resolution and storage for Electron environments.
 * Uses IPC to communicate with main process for server URL and storage.
 */

/**
 * Get the base server URL from Electron store
 * @returns {string} Base URL configured by user (e.g., "http://192.168.1.100:8080")
 */
export function baseURL() {
  // Check if electronAPI is available
  if (!window.electronAPI) {
    throw new Error(
      'Electron API not available. This should only be called in Electron environment.'
    );
  }

  // Get server URL from Electron store via synchronous IPC
  const serverURL = window.electronAPI.getServerURLSync?.() || null;

  if (!serverURL) {
    throw new Error('No server URL configured. Please select a server in the connection manager.');
  }

  return serverURL;
}

/**
 * Construct a full URL from a path
 * @param {string} path - Path to append (e.g., "/api/v1/show")
 * @returns {string} Full URL
 */
export function makeURL(path) {
  return `${baseURL()}${path}`;
}

/**
 * Get the application version
 * @returns {string} Version from Electron app
 */
export function getVersion() {
  if (window.electronAPI?.getAppVersion) {
    return window.electronAPI.getAppVersion();
  }
  return '0.23.0';
}

/**
 * Get storage adapter for Electron environment
 * Uses electron-store via IPC instead of browser storage
 * @param {string} type - Storage type ('local' or 'session')
 * @returns {Object} Storage adapter with getItem/setItem/removeItem/clear
 */
export function getStorageAdapter(type = 'local') {
  if (!window.electronAPI) {
    throw new Error('Electron API not available');
  }

  // For Electron, we use electron-store for both local and session storage
  // Session storage in Electron should persist across restarts (unlike browser)
  return {
    getItem(key) {
      return window.electronAPI.storageGet?.(key) || null;
    },
    setItem(key, value) {
      window.electronAPI.storageSet?.(key, value);
    },
    removeItem(key) {
      window.electronAPI.storageDelete?.(key);
    },
    clear() {
      window.electronAPI.storageClear?.();
    },
  };
}

/**
 * Get WebSocket URL for the configured server
 * @returns {string} WebSocket URL (e.g., "ws://192.168.1.100:8080/api/v1/ws")
 */
export function getWebSocketURL() {
  const base = baseURL();
  const url = new URL(base);
  const protocol = url.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${url.host}/api/v1/ws`;
}
