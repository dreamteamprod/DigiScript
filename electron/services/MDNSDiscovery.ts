import { Bonjour } from 'bonjour-service';
import VersionChecker from './VersionChecker.js';

export interface DiscoveredServer {
  name: string;
  host: string;
  port: number;
  url: string;
  addresses: string[];
  metadata: Record<string, string>;
}

export interface DiscoveredServerWithVersion extends DiscoveredServer {
  compatible: boolean;
  serverVersion: string | null;
  versionError: string | null;
}

class MDNSDiscovery {
  static async discoverServers(timeout = 5000): Promise<DiscoveredServer[]> {
    return new Promise((resolve) => {
      const bonjour = new Bonjour();
      const servers: DiscoveredServer[] = [];
      const seenHosts = new Set<string>();

      const browser = bonjour.find({ type: 'digiscript' });

      browser.on('up', (service) => {
        const hostId = `${service.host}:${service.port}`;

        if (seenHosts.has(hostId)) {
          return;
        }

        seenHosts.add(hostId);

        const txt = service.txt as Record<string, string> | undefined;
        const protocol = txt?.ssl === 'true' || txt?.https === 'true' ? 'https' : 'http';
        const addresses = service.addresses || [];

        servers.push({
          name: service.name || service.host,
          host: service.host,
          port: service.port,
          url: `${protocol}://${service.host}:${service.port}`,
          addresses,
          metadata: txt || {},
        });
      });

      setTimeout(() => {
        browser.stop();
        bonjour.destroy();
        resolve(servers);
      }, timeout);
    });
  }

  static async discoverServersWithVersionCheck(
    clientVersion: string,
    timeout = 5000
  ): Promise<DiscoveredServerWithVersion[]> {
    const servers = await MDNSDiscovery.discoverServers(timeout);

    return Promise.all(
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
  }

  static isMDNSAvailable(): boolean {
    return true;
  }
}

export default MDNSDiscovery;
