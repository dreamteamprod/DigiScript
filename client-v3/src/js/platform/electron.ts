export interface ElectronConnection {
  id: string;
  nickname: string;
  url: string;
  sslEnabled: boolean;
}

export interface ElectronVersionCheckResult {
  compatible: boolean;
  serverVersion?: string;
  error?: string;
}

export interface ElectronDiscoveredServer {
  name: string;
  url: string;
  compatible: boolean;
  serverVersion?: string;
  versionError?: string;
}

declare global {
  interface Window {
    electronAPI?: {
      getServerURLSync?: () => string | null;
      getAppVersion?: () => string;
      getActiveConnection?: () => Promise<ElectronConnection | null>;
      storageGet?: (key: string) => string | null;
      storageSet?: (key: string, value: string) => void;
      storageDelete?: (key: string) => void;
      storageClear?: () => void;
      getAllConnections?: () => Promise<ElectronConnection[]>;
      addConnection?: (conn: Omit<ElectronConnection, 'id'>) => Promise<ElectronConnection>;
      updateConnection?: (
        id: string,
        updates: Partial<ElectronConnection>
      ) => Promise<ElectronConnection>;
      deleteConnection?: (id: string) => Promise<void>;
      setActiveConnection?: (id: string) => Promise<void>;
      clearActiveConnection?: () => Promise<void>;
      checkVersion?: (serverUrl: string) => Promise<ElectronVersionCheckResult>;
      discoverServersWithVersionCheck?: (timeout?: number) => Promise<ElectronDiscoveredServer[]>;
    };
  }
}

export function baseURL(): string {
  if (!window.electronAPI) {
    throw new Error(
      'Electron API not available. This should only be called in Electron environment.'
    );
  }

  const serverURL = window.electronAPI.getServerURLSync?.() || null;

  if (!serverURL) {
    throw new Error('No server URL configured. Please select a server in the connection manager.');
  }

  return serverURL;
}

export function makeURL(path: string): string {
  return `${baseURL()}${path}`;
}

export function getVersion(): string {
  if (window.electronAPI?.getAppVersion) {
    return window.electronAPI.getAppVersion();
  }
  return '0.23.0';
}

export function getStorageAdapter(
  _type = 'local'
): Pick<Storage, 'getItem' | 'setItem' | 'removeItem' | 'clear'> {
  if (!window.electronAPI) {
    throw new Error('Electron API not available');
  }

  return {
    getItem(key: string): string | null {
      return window.electronAPI!.storageGet?.(key) ?? null;
    },
    setItem(key: string, value: string): void {
      window.electronAPI!.storageSet?.(key, value);
    },
    removeItem(key: string): void {
      window.electronAPI!.storageDelete?.(key);
    },
    clear(): void {
      window.electronAPI!.storageClear?.();
    },
  };
}

export function getWebSocketURL(): string {
  const base = baseURL();
  const url = new URL(base);
  const protocol = url.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${url.host}/api/v1/ws`;
}
