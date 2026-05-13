function isElectron(): boolean {
  return typeof window !== 'undefined' && window.electronAPI !== undefined;
}

let platformModule;

if (isElectron()) {
  platformModule = await import('./electron');
} else {
  platformModule = await import('./browser');
}

export const { baseURL, makeURL, getVersion, getStorageAdapter, getWebSocketURL } = platformModule;

export { isElectron };
