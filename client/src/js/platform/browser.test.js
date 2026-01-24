import { describe, it, expect, beforeEach, vi } from 'vitest';
import { baseURL, makeURL, getVersion, getStorageAdapter, getWebSocketURL } from './browser.js';

describe('browser.js', () => {
  describe('baseURL', () => {
    beforeEach(() => {
      // Reset location mock before each test
      delete window.location;
      window.location = {
        protocol: 'http:',
        hostname: 'localhost',
        port: '8080',
      };
    });

    it('should construct base URL from window.location', () => {
      const result = baseURL();
      expect(result).toBe('http://localhost:8080');
    });

    it('should handle HTTPS protocol', () => {
      window.location.protocol = 'https:';
      window.location.hostname = 'example.com';
      window.location.port = '443';

      const result = baseURL();
      expect(result).toBe('https://example.com:443');
    });

    it('should handle different hostnames', () => {
      window.location.hostname = '192.168.1.100';
      window.location.port = '3000';

      const result = baseURL();
      expect(result).toBe('http://192.168.1.100:3000');
    });

    it('should handle empty port', () => {
      window.location.port = '';

      const result = baseURL();
      expect(result).toBe('http://localhost:');
    });
  });

  describe('makeURL', () => {
    beforeEach(() => {
      delete window.location;
      window.location = {
        protocol: 'http:',
        hostname: 'localhost',
        port: '8080',
      };
    });

    it('should append path to base URL', () => {
      const result = makeURL('/api/v1/show');
      expect(result).toBe('http://localhost:8080/api/v1/show');
    });

    it('should handle paths without leading slash', () => {
      const result = makeURL('api/v1/show');
      expect(result).toBe('http://localhost:8080api/v1/show');
    });

    it('should handle empty path', () => {
      const result = makeURL('');
      expect(result).toBe('http://localhost:8080');
    });

    it('should handle paths with query parameters', () => {
      const result = makeURL('/api/v1/show?id=123');
      expect(result).toBe('http://localhost:8080/api/v1/show?id=123');
    });
  });

  describe('getVersion', () => {
    it('should return version from VITE_APP_VERSION', () => {
      // Mock import.meta.env
      vi.stubEnv('VITE_APP_VERSION', '1.2.3');

      const result = getVersion();
      expect(result).toBe('1.2.3');

      vi.unstubAllEnvs();
    });

    it('should return default version when VITE_APP_VERSION not set', () => {
      vi.stubEnv('VITE_APP_VERSION', undefined);

      const result = getVersion();
      expect(result).toBe('0.23.0');

      vi.unstubAllEnvs();
    });
  });

  describe('getStorageAdapter', () => {
    it('should return localStorage by default', () => {
      const storage = getStorageAdapter();
      expect(storage).toBe(window.localStorage);
    });

    it('should return localStorage when type is "local"', () => {
      const storage = getStorageAdapter('local');
      expect(storage).toBe(window.localStorage);
    });

    it('should return sessionStorage when type is "session"', () => {
      const storage = getStorageAdapter('session');
      expect(storage).toBe(window.sessionStorage);
    });

    it('should return localStorage for unknown types', () => {
      const storage = getStorageAdapter('unknown');
      expect(storage).toBe(window.localStorage);
    });
  });

  describe('getWebSocketURL', () => {
    beforeEach(() => {
      delete window.location;
      window.location = {
        protocol: 'http:',
        hostname: 'localhost',
        port: '8080',
      };
    });

    it('should construct ws URL for HTTP protocol', () => {
      const result = getWebSocketURL();
      expect(result).toBe('ws://localhost:8080/api/v1/ws');
    });

    it('should construct wss URL for HTTPS protocol', () => {
      window.location.protocol = 'https:';
      window.location.hostname = 'example.com';
      window.location.port = '443';

      const result = getWebSocketURL();
      expect(result).toBe('wss://example.com:443/api/v1/ws');
    });

    it('should handle different ports', () => {
      window.location.port = '3000';

      const result = getWebSocketURL();
      expect(result).toBe('ws://localhost:3000/api/v1/ws');
    });

    it('should handle IP addresses', () => {
      window.location.hostname = '192.168.1.100';
      window.location.port = '8080';

      const result = getWebSocketURL();
      expect(result).toBe('ws://192.168.1.100:8080/api/v1/ws');
    });
  });
});
