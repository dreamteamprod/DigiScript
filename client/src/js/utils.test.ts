import { describe, it, expect, beforeEach } from 'vitest';
import { baseURL, makeURL, getWebSocketURL } from './utils';

describe('utils URL helpers', () => {
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
      expect(result).toBe('http://localhost');
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
