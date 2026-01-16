/**
 * Browser Platform Implementation
 *
 * Provides URL resolution and storage for browser environments.
 * Uses window.location for URL construction (existing behavior).
 */

/**
 * Get the base server URL from the current browser location
 * @returns {string} Base URL (e.g., "http://localhost:8080")
 */
export function baseURL() {
  return `${window.location.protocol}//${window.location.hostname}:${window.location.port}`;
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
 * @returns {string} Version from environment
 */
export function getVersion() {
  return import.meta.env.VITE_APP_VERSION || '0.23.0';
}

/**
 * Get storage adapter for browser environment
 * @param {string} type - Storage type ('local' or 'session')
 * @returns {Storage} localStorage or sessionStorage
 */
export function getStorageAdapter(type = 'local') {
  return type === 'session' ? window.sessionStorage : window.localStorage;
}

/**
 * Get WebSocket URL for the current server
 * @returns {string} WebSocket URL (e.g., "ws://localhost:8080/api/v1/ws")
 */
export function getWebSocketURL() {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.hostname}:${window.location.port}/api/v1/ws`;
}
