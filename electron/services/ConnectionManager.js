/**
 * Connection Manager Service
 *
 * Manages server connections using electron-store for persistence.
 * Handles CRUD operations, active connection tracking, and general storage.
 */

import Store from 'electron-store';
import { randomUUID } from 'crypto';

class ConnectionManager {
  constructor() {
    // Initialize electron-store with schema
    this.store = new Store({
      name: 'digiscript-connections',
      schema: {
        connections: {
          type: 'array',
          default: [],
          items: {
            type: 'object',
            properties: {
              id: { type: 'string' },
              url: { type: 'string' },
              nickname: { type: 'string' },
              lastConnected: { type: ['number', 'null'] },
              sslEnabled: { type: 'boolean', default: false },
              // Optional credential storage
              username: { type: ['string', 'null'], default: null },
              // Store password hash or use safeStorage in Phase 6
              passwordHash: { type: ['string', 'null'], default: null },
            },
            required: ['id', 'url', 'nickname'],
          },
        },
        activeConnectionId: {
          type: ['string', 'null'],
          default: null,
        },
      },
    });

    // Separate store for general app storage (Vuex persistence, etc.)
    this.appStore = new Store({
      name: 'digiscript-app-storage',
    });
  }

  /**
   * Get all saved connections
   * @returns {Array} Array of connection objects
   */
  getAllConnections() {
    return this.store.get('connections', []);
  }

  /**
   * Get a connection by ID
   * @param {string} id - Connection ID
   * @returns {Object|null} Connection object or null if not found
   */
  getConnectionById(id) {
    const connections = this.getAllConnections();
    return connections.find((conn) => conn.id === id) || null;
  }

  /**
   * Add a new connection
   * @param {Object} connection - Connection details {url, nickname, sslEnabled?, username?, passwordHash?}
   * @returns {Object} The created connection with generated ID
   */
  addConnection(connection) {
    const connections = this.getAllConnections();

    // Generate unique ID
    const newConnection = {
      id: randomUUID(),
      url: connection.url,
      nickname: connection.nickname,
      lastConnected: null,
      sslEnabled: connection.sslEnabled || false,
      username: connection.username || null,
      passwordHash: connection.passwordHash || null,
    };

    connections.push(newConnection);
    this.store.set('connections', connections);

    return newConnection;
  }

  /**
   * Update an existing connection
   * @param {string} id - Connection ID
   * @param {Object} updates - Fields to update
   * @returns {Object|null} Updated connection or null if not found
   */
  updateConnection(id, updates) {
    const connections = this.getAllConnections();
    const index = connections.findIndex((conn) => conn.id === id);

    if (index === -1) {
      return null;
    }

    // Update connection (preserve ID and immutable fields)
    connections[index] = {
      ...connections[index],
      ...updates,
      id, // Ensure ID cannot be changed
    };

    this.store.set('connections', connections);
    return connections[index];
  }

  /**
   * Delete a connection
   * @param {string} id - Connection ID
   * @returns {boolean} True if deleted, false if not found
   */
  deleteConnection(id) {
    const connections = this.getAllConnections();
    const filtered = connections.filter((conn) => conn.id !== id);

    if (filtered.length === connections.length) {
      return false; // Connection not found
    }

    this.store.set('connections', filtered);

    // Clear active connection if it was deleted
    if (this.store.get('activeConnectionId') === id) {
      this.store.set('activeConnectionId', null);
    }

    return true;
  }

  /**
   * Get the active connection
   * @returns {Object|null} Active connection or null
   */
  getActiveConnection() {
    const activeId = this.store.get('activeConnectionId');
    if (!activeId) {
      return null;
    }
    return this.getConnectionById(activeId);
  }

  /**
   * Set the active connection
   * @param {string} id - Connection ID to activate
   * @returns {Object|null} Activated connection or null if not found
   */
  setActiveConnection(id) {
    const connection = this.getConnectionById(id);
    if (!connection) {
      return null;
    }

    // Update last connected timestamp
    this.updateConnection(id, {
      lastConnected: Date.now(),
    });

    // Set as active
    this.store.set('activeConnectionId', id);

    return this.getConnectionById(id); // Return updated connection
  }

  /**
   * Clear the active connection (disconnect)
   * @returns {void}
   */
  clearActiveConnection() {
    this.store.set('activeConnectionId', null);
  }

  // =============================================================================
  // General Storage Methods (for Vuex persistence and platform layer)
  // =============================================================================

  /**
   * Get a storage item
   * @param {string} key - Storage key
   * @returns {any} Stored value or null
   */
  getStorageItem(key) {
    return this.appStore.get(key, null);
  }

  /**
   * Set a storage item
   * @param {string} key - Storage key
   * @param {any} value - Value to store
   * @returns {void}
   */
  setStorageItem(key, value) {
    this.appStore.set(key, value);
  }

  /**
   * Delete a storage item
   * @param {string} key - Storage key
   * @returns {void}
   */
  deleteStorageItem(key) {
    this.appStore.delete(key);
  }

  /**
   * Clear all storage items
   * @returns {void}
   */
  clearStorage() {
    this.appStore.clear();
  }
}

export default ConnectionManager;
