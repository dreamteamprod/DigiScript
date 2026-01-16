/**
 * Version Checker Service
 *
 * Validates server compatibility by comparing versions.
 * Requires exact version match between client and server.
 */

const fetch = require('node-fetch');

class VersionChecker {
  /**
   * Check if a server is compatible with this client
   * @param {string} serverUrl - Base URL of the server (e.g., "http://192.168.1.100:8080")
   * @param {string} clientVersion - Client version (e.g., "0.23.0")
   * @returns {Promise<Object>} Result object with compatibility info
   */
  static async checkVersion(serverUrl, clientVersion) {
    const result = {
      compatible: false,
      serverVersion: null,
      clientVersion,
      serverUrl,
      error: null,
    };

    try {
      // Construct the settings endpoint URL
      const settingsUrl = `${serverUrl}/api/v1/settings`;

      // Fetch server settings with timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 second timeout

      const response = await fetch(settingsUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Check if request was successful
      if (!response.ok) {
        result.error = `Server returned ${response.status}: ${response.statusText}`;
        return result;
      }

      // Parse JSON response
      const settings = await response.json();

      // Extract version from settings
      if (!settings || !settings.version) {
        result.error = 'Server response does not contain version information';
        return result;
      }

      result.serverVersion = settings.version;

      // Compare versions (exact match required)
      result.compatible = result.serverVersion === clientVersion;

      if (!result.compatible) {
        result.error = `Version mismatch: Client ${clientVersion} requires Server ${clientVersion}, but found ${result.serverVersion}`;
      }

      return result;
    } catch (error) {
      // Handle various error types
      if (error.name === 'AbortError') {
        result.error = 'Connection timeout: Server did not respond within 5 seconds';
      } else if (error.code === 'ECONNREFUSED') {
        result.error = 'Connection refused: Server is not running or unreachable';
      } else if (error.code === 'ENOTFOUND') {
        result.error = 'Host not found: Invalid server URL or DNS resolution failed';
      } else if (error.code === 'ETIMEDOUT') {
        result.error = 'Connection timeout: Network unreachable';
      } else {
        result.error = `Error checking version: ${error.message}`;
      }

      return result;
    }
  }

  /**
   * Validate server URL format
   * @param {string} url - URL to validate
   * @returns {boolean} True if valid, false otherwise
   */
  static isValidUrl(url) {
    try {
      const parsed = new URL(url);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  }

  /**
   * Normalize server URL (remove trailing slash, ensure protocol)
   * @param {string} url - URL to normalize
   * @returns {string} Normalized URL
   */
  static normalizeUrl(url) {
    // Remove trailing slash
    let normalized = url.replace(/\/$/, '');

    // Add protocol if missing
    if (!normalized.startsWith('http://') && !normalized.startsWith('https://')) {
      normalized = `http://${normalized}`;
    }

    return normalized;
  }
}

module.exports = VersionChecker;
