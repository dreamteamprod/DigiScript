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
export function baseURL(): string {
  return `${window.location.protocol}//${window.location.hostname}${window.location.port ? ':' + window.location.port : '' }`;
}

export function makeURL(path: string): string {
  return `${baseURL()}${path}`;
}

export function getVersion(): string {
  return import.meta.env.VITE_APP_VERSION || '0.23.0';
}

export function getStorageAdapter(type = 'local'): Storage {
  return type === 'session' ? window.sessionStorage : window.localStorage;
}

export function getWebSocketURL(): string {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.hostname}:${window.location.port}/api/v1/ws`;
}
