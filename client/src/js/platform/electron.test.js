import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { baseURL, makeURL, getVersion, getStorageAdapter, getWebSocketURL } from './electron.js';

describe('electron.js', () => {
  describe('baseURL', () => {
    beforeEach(() => {
      // Mock window.electronAPI
      global.window = global.window || {};
      window.electronAPI = {
        getServerURLSync: vi.fn(() => 'http://192.168.1.100:8080'),
      };
    });

    afterEach(() => {
      delete window.electronAPI;
    });

    it('should return server URL from electronAPI', () => {
      const result = baseURL();
      expect(result).toBe('http://192.168.1.100:8080');
      expect(window.electronAPI.getServerURLSync).toHaveBeenCalled();
    });

    it('should throw error when electronAPI is not available', () => {
      delete window.electronAPI;

      expect(() => baseURL()).toThrow(
        'Electron API not available. This should only be called in Electron environment.'
      );
    });

    it('should throw error when no server URL is configured', () => {
      window.electronAPI.getServerURLSync = vi.fn(() => null);

      expect(() => baseURL()).toThrow(
        'No server URL configured. Please select a server in the connection manager.'
      );
    });

    it('should throw error when getServerURLSync returns empty string', () => {
      window.electronAPI.getServerURLSync = vi.fn(() => '');

      expect(() => baseURL()).toThrow(
        'No server URL configured. Please select a server in the connection manager.'
      );
    });

    it('should handle HTTPS URLs', () => {
      window.electronAPI.getServerURLSync = vi.fn(() => 'https://example.com:443');

      const result = baseURL();
      expect(result).toBe('https://example.com:443');
    });

    it('should handle URLs without port', () => {
      window.electronAPI.getServerURLSync = vi.fn(() => 'http://example.com');

      const result = baseURL();
      expect(result).toBe('http://example.com');
    });
  });

  describe('makeURL', () => {
    beforeEach(() => {
      global.window = global.window || {};
      window.electronAPI = {
        getServerURLSync: vi.fn(() => 'http://192.168.1.100:8080'),
      };
    });

    afterEach(() => {
      delete window.electronAPI;
    });

    it('should append path to base URL', () => {
      const result = makeURL('/api/v1/show');
      expect(result).toBe('http://192.168.1.100:8080/api/v1/show');
    });

    it('should handle paths without leading slash', () => {
      const result = makeURL('api/v1/show');
      expect(result).toBe('http://192.168.1.100:8080api/v1/show');
    });

    it('should handle empty path', () => {
      const result = makeURL('');
      expect(result).toBe('http://192.168.1.100:8080');
    });

    it('should handle paths with query parameters', () => {
      const result = makeURL('/api/v1/show?id=123');
      expect(result).toBe('http://192.168.1.100:8080/api/v1/show?id=123');
    });

    it('should throw error when baseURL fails', () => {
      delete window.electronAPI;

      expect(() => makeURL('/api/v1/show')).toThrow('Electron API not available');
    });
  });

  describe('getVersion', () => {
    afterEach(() => {
      delete window.electronAPI;
    });

    it('should return version from electronAPI', () => {
      window.electronAPI = {
        getAppVersion: vi.fn(() => '1.2.3'),
      };

      const result = getVersion();
      expect(result).toBe('1.2.3');
      expect(window.electronAPI.getAppVersion).toHaveBeenCalled();
    });

    it('should return default version when electronAPI not available', () => {
      delete window.electronAPI;

      const result = getVersion();
      expect(result).toBe('0.23.0');
    });

    it('should return default version when getAppVersion not available', () => {
      window.electronAPI = {};

      const result = getVersion();
      expect(result).toBe('0.23.0');
    });
  });

  describe('getStorageAdapter', () => {
    beforeEach(() => {
      global.window = global.window || {};
      window.electronAPI = {
        storageGet: vi.fn(),
        storageSet: vi.fn(),
        storageDelete: vi.fn(),
        storageClear: vi.fn(),
      };
    });

    afterEach(() => {
      delete window.electronAPI;
    });

    it('should throw error when electronAPI not available', () => {
      delete window.electronAPI;

      expect(() => getStorageAdapter()).toThrow('Electron API not available');
    });

    it('should return storage adapter for local storage by default', () => {
      const storage = getStorageAdapter();

      expect(storage).toHaveProperty('getItem');
      expect(storage).toHaveProperty('setItem');
      expect(storage).toHaveProperty('removeItem');
      expect(storage).toHaveProperty('clear');
    });

    it('should return storage adapter for session storage', () => {
      const storage = getStorageAdapter('session');

      expect(storage).toHaveProperty('getItem');
      expect(storage).toHaveProperty('setItem');
      expect(storage).toHaveProperty('removeItem');
      expect(storage).toHaveProperty('clear');
    });

    describe('storage adapter methods', () => {
      it('getItem should call electronAPI.storageGet', () => {
        window.electronAPI.storageGet = vi.fn(() => 'test-value');

        const storage = getStorageAdapter();
        const result = storage.getItem('test-key');

        expect(result).toBe('test-value');
        expect(window.electronAPI.storageGet).toHaveBeenCalledWith('test-key');
      });

      it('getItem should return null when storageGet returns null', () => {
        window.electronAPI.storageGet = vi.fn(() => null);

        const storage = getStorageAdapter();
        const result = storage.getItem('non-existent');

        expect(result).toBeNull();
      });

      it('getItem should return null when storageGet not available', () => {
        delete window.electronAPI.storageGet;

        const storage = getStorageAdapter();
        const result = storage.getItem('test-key');

        expect(result).toBeNull();
      });

      it('setItem should call electronAPI.storageSet', () => {
        const storage = getStorageAdapter();
        storage.setItem('test-key', 'test-value');

        expect(window.electronAPI.storageSet).toHaveBeenCalledWith('test-key', 'test-value');
      });

      it('setItem should not throw when storageSet not available', () => {
        delete window.electronAPI.storageSet;

        const storage = getStorageAdapter();
        expect(() => storage.setItem('test-key', 'test-value')).not.toThrow();
      });

      it('removeItem should call electronAPI.storageDelete', () => {
        const storage = getStorageAdapter();
        storage.removeItem('test-key');

        expect(window.electronAPI.storageDelete).toHaveBeenCalledWith('test-key');
      });

      it('removeItem should not throw when storageDelete not available', () => {
        delete window.electronAPI.storageDelete;

        const storage = getStorageAdapter();
        expect(() => storage.removeItem('test-key')).not.toThrow();
      });

      it('clear should call electronAPI.storageClear', () => {
        const storage = getStorageAdapter();
        storage.clear();

        expect(window.electronAPI.storageClear).toHaveBeenCalled();
      });

      it('clear should not throw when storageClear not available', () => {
        delete window.electronAPI.storageClear;

        const storage = getStorageAdapter();
        expect(() => storage.clear()).not.toThrow();
      });
    });
  });

  describe('getWebSocketURL', () => {
    beforeEach(() => {
      global.window = global.window || {};
      window.electronAPI = {
        getServerURLSync: vi.fn(() => 'http://192.168.1.100:8080'),
      };
    });

    afterEach(() => {
      delete window.electronAPI;
    });

    it('should construct ws URL for HTTP base URL', () => {
      const result = getWebSocketURL();
      expect(result).toBe('ws://192.168.1.100:8080/api/v1/ws');
    });

    it('should construct wss URL for HTTPS base URL', () => {
      window.electronAPI.getServerURLSync = vi.fn(() => 'https://example.com:443');

      const result = getWebSocketURL();
      // URL object normalizes default ports (443 for https)
      expect(result).toBe('wss://example.com/api/v1/ws');
    });

    it('should handle URLs without explicit port', () => {
      window.electronAPI.getServerURLSync = vi.fn(() => 'http://example.com');

      const result = getWebSocketURL();
      expect(result).toBe('ws://example.com/api/v1/ws');
    });

    it('should handle different ports', () => {
      window.electronAPI.getServerURLSync = vi.fn(() => 'http://localhost:3000');

      const result = getWebSocketURL();
      expect(result).toBe('ws://localhost:3000/api/v1/ws');
    });

    it('should throw error when baseURL fails', () => {
      window.electronAPI.getServerURLSync = vi.fn(() => null);

      expect(() => getWebSocketURL()).toThrow(
        'No server URL configured. Please select a server in the connection manager.'
      );
    });
  });
});
