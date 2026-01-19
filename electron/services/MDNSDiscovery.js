/**
 * mDNS Discovery Service
 *
 * Discovers DigiScript servers on the local network using mDNS/DNS-SD.
 * Requires servers to advertise themselves via Bonjour/Zeroconf.
 */

const { Bonjour } = require('bonjour-service');

class MDNSDiscovery {
  /**
   * Discover DigiScript servers on the local network
   * @param {number} timeout - Discovery timeout in milliseconds (default: 5000)
   * @returns {Promise<Array>} Array of discovered servers [{name, host, port, url, addresses}]
   */
  static async discoverServers(timeout = 5000) {
    return new Promise((resolve) => {
      const bonjour = new Bonjour();
      const servers = [];
      const seenHosts = new Set(); // Prevent duplicates

      // Browse for DigiScript services
      // Service type: _digiscript._tcp
      const browser = bonjour.find({ type: 'digiscript' });

      // Handle discovered services
      browser.on('up', (service) => {
        // Create unique identifier for this service
        const hostId = `${service.host}:${service.port}`;

        // Skip if we've already seen this host/port combination
        if (seenHosts.has(hostId)) {
          return;
        }

        seenHosts.add(hostId);

        // Determine protocol (default to http, check txt records for https)
        const protocol = service.txt?.ssl === 'true' || service.txt?.https === 'true' ? 'https' : 'http';

        // Extract addresses
        const addresses = service.addresses || [];

        // Build server object
        const server = {
          name: service.name || service.host,
          host: service.host,
          port: service.port,
          url: `${protocol}://${service.host}:${service.port}`,
          addresses,
          // Optional: Include additional txt record data
          metadata: service.txt || {},
        };

        servers.push(server);
      });

      // Stop discovery after timeout
      setTimeout(() => {
        browser.stop();
        bonjour.destroy();
        resolve(servers);
      }, timeout);
    });
  }

  /**
   * Discover servers and check their versions
   * @param {string} clientVersion - Client version to check against
   * @param {number} timeout - Discovery timeout in milliseconds (default: 5000)
   * @returns {Promise<Array>} Array of servers with version compatibility info
   */
  static async discoverServersWithVersionCheck(clientVersion, timeout = 5000) {
    const VersionChecker = require('./VersionChecker');

    // First, discover all servers
    const servers = await MDNSDiscovery.discoverServers(timeout);

    // Then, check version for each discovered server
    const serversWithVersions = await Promise.all(
      servers.map(async (server) => {
        const versionResult = await VersionChecker.checkVersion(server.url, clientVersion);

        return {
          ...server,
          compatible: versionResult.compatible,
          serverVersion: versionResult.serverVersion,
          versionError: versionResult.error,
        };
      })
    );

    return serversWithVersions;
  }

  /**
   * Check if mDNS is available on the system
   * @returns {boolean} True if mDNS is likely available
   */
  static isMDNSAvailable() {
    // mDNS is typically available on:
    // - macOS (via Bonjour)
    // - Windows (if Bonjour service is installed)
    // - Linux (via Avahi)

    // For now, assume it's available and let errors surface during discovery
    return true;
  }
}

module.exports = MDNSDiscovery;
