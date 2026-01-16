/**
 * Platform Abstraction Layer
 *
 * Detects the runtime environment (browser vs Electron) and exports
 * the appropriate platform implementation.
 *
 * This allows the Vue app to work seamlessly in both web browsers
 * and Electron without conditional logic scattered throughout the codebase.
 */

/**
 * Detect if running in Electron environment
 * @returns {boolean} True if running in Electron
 */
function isElectron() {
  // Check if the Electron API is exposed via preload script
  return typeof window !== 'undefined' && window.electronAPI !== undefined;
}

// Dynamically import and export the appropriate platform implementation
let platformModule;

if (isElectron()) {
  // Running in Electron - use IPC-based implementation
  platformModule = await import('./electron.js');
} else {
  // Running in browser - use window.location-based implementation
  platformModule = await import('./browser.js');
}

// Re-export all platform functions
export const { baseURL, makeURL, getVersion, getStorageAdapter, getWebSocketURL } = platformModule;

/**
 * Check if currently running in Electron
 * @returns {boolean}
 */
export { isElectron };
