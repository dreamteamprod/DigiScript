interface VersionCheckResult {
  compatible: boolean;
  serverVersion: string | null;
  clientVersion: string;
  serverUrl: string;
  error: string | null;
}

class VersionChecker {
  static async checkVersion(serverUrl: string, clientVersion: string): Promise<VersionCheckResult> {
    const result: VersionCheckResult = {
      compatible: false,
      serverVersion: null,
      clientVersion,
      serverUrl,
      error: null,
    };

    try {
      const healthUrl = `${serverUrl}/api/v1/health`;

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);

      const response = await fetch(healthUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        result.error = `Server returned ${response.status}: ${response.statusText}`;
        return result;
      }

      const health = (await response.json()) as { version?: string } | null;

      if (!health || !health.version) {
        result.error = 'Server response does not contain version information';
        return result;
      }

      result.serverVersion = health.version;
      result.compatible = result.serverVersion === clientVersion;

      if (!result.compatible) {
        result.error = `Version mismatch: Client ${clientVersion} requires Server ${clientVersion}, but found ${result.serverVersion}`;
      }

      return result;
    } catch (err: unknown) {
      const error = err as NodeJS.ErrnoException;
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

  static isValidUrl(url: string): boolean {
    try {
      const parsed = new URL(url);
      return parsed.protocol === 'http:' || parsed.protocol === 'https:';
    } catch {
      return false;
    }
  }

  static normalizeUrl(url: string): string {
    let normalized = url.replace(/\/$/, '');

    if (!normalized.startsWith('http://') && !normalized.startsWith('https://')) {
      normalized = `http://${normalized}`;
    }

    return normalized;
  }
}

export default VersionChecker;
