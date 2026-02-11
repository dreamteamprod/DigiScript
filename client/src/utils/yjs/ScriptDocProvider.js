/**
 * Custom Yjs provider that uses DigiScript's existing WebSocket connection.
 *
 * Instead of opening a separate WebSocket (like y-websocket would),
 * this provider sends Yjs sync messages via the existing managed
 * connection using custom OP codes.
 *
 * Message flow:
 *   JOIN_SCRIPT_ROOM → server creates/loads room → YJS_SYNC step 0 (full state)
 *   YJS_UPDATE ←→ incremental document updates
 *   YJS_AWARENESS ←→ presence/cursor state
 *   LEAVE_SCRIPT_ROOM → server removes client from room
 */

import Vue from 'vue';
import * as Y from 'yjs';
import log from 'loglevel';

/**
 * Encode a Uint8Array to base64 string for JSON transport.
 * @param {Uint8Array} uint8Array
 * @returns {string}
 */
function encodeBase64(uint8Array) {
  let binary = '';
  for (let i = 0; i < uint8Array.length; i++) {
    binary += String.fromCharCode(uint8Array[i]);
  }
  return btoa(binary);
}

/**
 * Decode a base64 string to Uint8Array.
 * @param {string} base64
 * @returns {Uint8Array}
 */
function decodeBase64(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export default class ScriptDocProvider {
  /**
   * @param {Y.Doc} doc - The Yjs document to sync
   * @param {number} revisionId - The script revision ID for the room
   * @param {object} options
   * @param {string} [options.role='editor'] - 'editor' or 'viewer'
   */
  constructor(doc, revisionId, options = {}) {
    this.doc = doc;
    this.revisionId = revisionId;
    this.roomId = `draft_${revisionId}`;
    this.role = options.role || 'editor';

    this._connected = false;
    this._synced = false;
    this._destroyed = false;
    this._updateHandler = null;

    // Bind the update handler
    this._onDocUpdate = this._onDocUpdate.bind(this);
  }

  /**
   * Get the WebSocket instance.
   * @returns {WebSocket|null}
   */
  get _socket() {
    return Vue.prototype.$socket || null;
  }

  /**
   * Connect to the collaborative editing room.
   * Sends JOIN_SCRIPT_ROOM and starts listening for updates.
   */
  connect() {
    if (this._destroyed) return;

    const socket = this._socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      log.warn('ScriptDocProvider: WebSocket not ready, deferring connect');
      return;
    }

    // Join the room
    socket.sendObj({
      OP: 'JOIN_SCRIPT_ROOM',
      DATA: {
        revision_id: this.revisionId,
        role: this.role,
      },
    });

    // Listen for local doc changes to broadcast
    this.doc.on('update', this._onDocUpdate);

    this._connected = true;
    log.info(`ScriptDocProvider: Joining room ${this.roomId} as ${this.role}`);
  }

  /**
   * Disconnect from the collaborative editing room.
   */
  disconnect() {
    if (!this._connected) return;

    const socket = this._socket;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.sendObj({
        OP: 'LEAVE_SCRIPT_ROOM',
        DATA: { room_id: this.roomId },
      });
    }

    this.doc.off('update', this._onDocUpdate);
    this._connected = false;
    this._synced = false;
    log.info(`ScriptDocProvider: Left room ${this.roomId}`);
  }

  /**
   * Permanently destroy this provider. Cannot be reconnected after.
   */
  destroy() {
    this.disconnect();
    this._destroyed = true;
  }

  /**
   * Handle an incoming WebSocket message from the server.
   * Should be called from the Vuex SOCKET_ONMESSAGE handler.
   *
   * @param {object} message - The parsed WebSocket message
   * @returns {boolean} true if this message was handled
   */
  handleMessage(message) {
    if (!this._connected && message.OP !== 'YJS_SYNC') return false;

    const data = message.DATA || {};
    if (data.room_id && data.room_id !== this.roomId) return false;

    switch (message.OP) {
      case 'YJS_SYNC':
        return this._handleSync(data);
      case 'YJS_UPDATE':
        return this._handleUpdate(data);
      case 'YJS_AWARENESS':
        return this._handleAwareness(data);
      default:
        return false;
    }
  }

  /**
   * Handle YJS_SYNC messages from the server.
   * @param {object} data
   * @returns {boolean}
   */
  _handleSync(data) {
    const payload = data.payload;
    if (!payload) return false;

    try {
      const decoded = decodeBase64(payload);

      if (data.step === 0) {
        // Initial full state from server
        Y.applyUpdate(this.doc, decoded, 'server');
        this._synced = true;
        log.info(`ScriptDocProvider: Synced with room ${this.roomId}`);

        // Send our state vector so server knows what we have
        const stateVector = Y.encodeStateVector(this.doc);
        this._sendToServer('YJS_SYNC', {
          step: 1,
          payload: encodeBase64(stateVector),
          room_id: this.roomId,
        });
      } else if (data.step === 2) {
        // Server's diff response to our state vector
        Y.applyUpdate(this.doc, decoded, 'server');
      }
    } catch (e) {
      log.error('ScriptDocProvider: Failed to handle sync message', e);
    }

    return true;
  }

  /**
   * Handle YJS_UPDATE messages from the server (other clients' changes).
   * @param {object} data
   * @returns {boolean}
   */
  _handleUpdate(data) {
    const payload = data.payload;
    if (!payload) return false;

    try {
      const decoded = decodeBase64(payload);
      Y.applyUpdate(this.doc, decoded, 'server');
    } catch (e) {
      log.error('ScriptDocProvider: Failed to apply update', e);
    }

    return true;
  }

  /**
   * Handle YJS_AWARENESS messages from the server.
   * @param {object} data
   * @returns {boolean}
   */
  _handleAwareness(data) {
    // Awareness handling will be implemented in Phase 3
    return true;
  }

  /**
   * Called when the local Y.Doc is updated.
   * Broadcasts the update to the server for other clients.
   *
   * @param {Uint8Array} update
   * @param {*} origin - 'server' if from remote, otherwise local
   */
  _onDocUpdate(update, origin) {
    // Don't echo back updates that came from the server
    if (origin === 'server') return;
    if (!this._connected) return;

    this._sendToServer('YJS_UPDATE', {
      payload: encodeBase64(update),
      room_id: this.roomId,
    });
  }

  /**
   * Send a message to the server via the existing WebSocket.
   * @param {string} op - The OP code
   * @param {object} data - The DATA payload
   */
  _sendToServer(op, data) {
    const socket = this._socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      log.warn('ScriptDocProvider: Cannot send, WebSocket not connected');
      return;
    }

    socket.sendObj({ OP: op, DATA: data });
  }

  /** @returns {boolean} Whether the provider is connected to a room */
  get connected() {
    return this._connected;
  }

  /** @returns {boolean} Whether the initial sync is complete */
  get synced() {
    return this._synced;
  }
}

export { encodeBase64, decodeBase64 };
