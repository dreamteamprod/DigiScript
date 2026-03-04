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
 *
 * The server is the authoritative source for which revision the room belongs
 * to. The client does not send a revision_id when joining — the server picks
 * the current revision automatically. Outgoing and incoming messages no longer
 * include a room_id field (there is only ever one room per server).
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
   * @param {object} options
   * @param {string} [options.role='editor'] - 'editor' or 'viewer'
   */
  constructor(doc, options = {}) {
    this.doc = doc;
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
   * The server determines which revision to join automatically.
   */
  connect() {
    if (this._destroyed) return;

    const socket = this._socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      log.warn('ScriptDocProvider: WebSocket not ready, deferring connect');
      return;
    }

    // Join the room — no revision_id needed; the server resolves it
    socket.sendObj({
      OP: 'JOIN_SCRIPT_ROOM',
      DATA: { role: this.role },
    });

    // Listen for local doc changes to broadcast
    this.doc.on('update', this._onDocUpdate);

    this._connected = true;
    log.info(`ScriptDocProvider: Joining room as ${this.role}`);
  }

  /**
   * Disconnect from the collaborative editing room.
   */
  disconnect() {
    if (!this._connected) return;

    // Clear local awareness before leaving
    this.setLocalAwareness({ page: null, lineIndex: null });

    const socket = this._socket;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.sendObj({ OP: 'LEAVE_SCRIPT_ROOM', DATA: {} });
    }

    this.doc.off('update', this._onDocUpdate);
    this._connected = false;
    this._synced = false;
    log.info('ScriptDocProvider: Left room');
  }

  /**
   * Permanently destroy this provider. Cannot be reconnected after.
   */
  destroy() {
    this.disconnect();
    this._destroyed = true;
  }

  /**
   * Apply a YJS_SYNC message from the server.
   * Accepts sync messages even before the room is marked connected,
   * since step 0 is what triggers the connected state.
   *
   * @param {object} data - The DATA payload from the server message
   * @returns {boolean} true if handled, false if filtered
   */
  applySync(data) {
    const payload = data.payload;
    if (!payload) return false;

    try {
      const decoded = decodeBase64(payload);

      if (data.step === 0) {
        // Initial full state from server
        log.debug(
          `ScriptDocProvider: Received step 0 (${decoded.length} bytes); applying full state`
        );
        Y.applyUpdate(this.doc, decoded, 'server');
        this._synced = true;
        log.info('ScriptDocProvider: Synced with room');

        // Send our state vector so server knows what we have
        const stateVector = Y.encodeStateVector(this.doc);
        this._sendToServer('YJS_SYNC', {
          step: 1,
          payload: encodeBase64(stateVector),
        });
      } else if (data.step === 2) {
        // Server's diff response to our state vector
        log.debug(`ScriptDocProvider: Received step 2 diff (${decoded.length} bytes); applied`);
        Y.applyUpdate(this.doc, decoded, 'server');
      }
    } catch (e) {
      log.error('ScriptDocProvider: Failed to handle sync message', e);
    }

    return true;
  }

  /**
   * Apply a YJS_UPDATE message from the server (other clients' changes).
   * Requires the room to be connected.
   *
   * @param {object} data - The DATA payload from the server message
   * @returns {boolean} true if handled, false if filtered
   */
  applyUpdate(data) {
    if (!this._connected) return false;
    const payload = data.payload;
    if (!payload) return false;

    try {
      const decoded = decodeBase64(payload);
      log.debug(`ScriptDocProvider: Applied remote update (${decoded.length} bytes)`);
      Y.applyUpdate(this.doc, decoded, 'server');
    } catch (e) {
      log.error('ScriptDocProvider: Failed to apply update', e);
    }

    return true;
  }

  /**
   * Apply a YJS_AWARENESS message from the server.
   * Requires the room to be connected.
   * Returns the decoded awareness state object for the Vuex store to process.
   *
   * @param {object} data - The DATA payload from the server message
   * @returns {object|boolean} awareness result object, true (no payload), or false (filtered)
   */
  applyAwareness(data) {
    if (!this._connected) return false;
    const payload = data.payload;
    if (!payload) return true;

    try {
      const decoded = decodeBase64(payload);
      const jsonStr = new TextDecoder().decode(decoded);
      const awarenessState = JSON.parse(jsonStr);
      return { type: 'AWARENESS', state: awarenessState };
    } catch (e) {
      log.error('ScriptDocProvider: Failed to handle awareness message', e);
    }

    return true;
  }

  /**
   * Set local awareness state and broadcast to other clients.
   * Used to share which line the user is currently editing.
   *
   * @param {object} state - e.g. { page, lineIndex, userId, username }
   */
  setLocalAwareness(state) {
    if (!this._connected) return;

    const jsonStr = JSON.stringify(state);
    const encoded = new TextEncoder().encode(jsonStr);
    this._sendToServer('YJS_AWARENESS', { payload: encodeBase64(encoded) });
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
    if (!this._connected) {
      log.debug(`ScriptDocProvider: _onDocUpdate suppressed (not connected, origin=${origin})`);
      return;
    }
    if (!this._synced) {
      log.debug(`ScriptDocProvider: _onDocUpdate suppressed (not yet synced, origin=${origin})`);
      return;
    }

    log.debug(`ScriptDocProvider: _onDocUpdate sending ${update.length}B (origin=${origin})`);
    this._sendToServer('YJS_UPDATE', { payload: encodeBase64(update) });
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
