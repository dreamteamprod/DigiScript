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
 * The server determines which revision the room belongs to automatically;
 * there is only ever one active room per server.
 */

import Vue from 'vue';
import * as Y from 'yjs';
import log from 'loglevel';

function encodeBase64(uint8Array) {
  let binary = '';
  for (let i = 0; i < uint8Array.length; i++) {
    binary += String.fromCharCode(uint8Array[i]);
  }
  return btoa(binary);
}

function decodeBase64(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

export default class ScriptDocProvider {
  constructor(doc, options = {}) {
    this.doc = doc;
    this.role = options.role || 'editor';
    this._connected = false;
    this._synced = false;
    this._destroyed = false;
    this._updateHandler = null;
    this._onDocUpdate = this._onDocUpdate.bind(this);
  }
  get _socket() {
    return Vue.prototype.$socket || null;
  }
  connect() {
    if (this._destroyed) return;
    const socket = this._socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      log.warn('ScriptDocProvider: WebSocket not ready, deferring connect');
      return;
    }
    socket.sendObj({
      OP: 'JOIN_SCRIPT_ROOM',
      DATA: { role: this.role },
    });
    this.doc.on('update', this._onDocUpdate);
    this._connected = true;
    log.info(`ScriptDocProvider: Joining room as ${this.role}`);
  }
  disconnect() {
    if (!this._connected) return;
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
  destroy() {
    this.disconnect();
    this._destroyed = true;
  }
  // Apply a YJS_SYNC message from the server.
  // Accepts sync messages even before the room is marked connected,
  // since step 0 is what triggers the connected state.
  applySync(data) {
    const payload = data.payload;
    if (!payload) return false;

    try {
      const decoded = decodeBase64(payload);

      if (data.step === 0) {
        log.debug(
          `ScriptDocProvider: Received step 0 (${decoded.length} bytes); applying full state`
        );
        Y.applyUpdate(this.doc, decoded, 'server');
        this._synced = true;
        log.info('ScriptDocProvider: Synced with room');
        const stateVector = Y.encodeStateVector(this.doc);
        this._sendToServer('YJS_SYNC', {
          step: 1,
          payload: encodeBase64(stateVector),
        });
      } else if (data.step === 2) {
        log.debug(`ScriptDocProvider: Received step 2 diff (${decoded.length} bytes); applied`);
        Y.applyUpdate(this.doc, decoded, 'server');
      }
    } catch (e) {
      log.error('ScriptDocProvider: Failed to handle sync message', e);
    }

    return true;
  }
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
  setLocalAwareness(state) {
    if (!this._connected) return;
    const jsonStr = JSON.stringify(state);
    const encoded = new TextEncoder().encode(jsonStr);
    this._sendToServer('YJS_AWARENESS', { payload: encodeBase64(encoded) });
  }
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
  _sendToServer(op, data) {
    const socket = this._socket;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      log.warn('ScriptDocProvider: Cannot send, WebSocket not connected');
      return;
    }
    socket.sendObj({ OP: op, DATA: data });
  }
  get connected() {
    return this._connected;
  }
  get synced() {
    return this._synced;
  }
}

export { encodeBase64, decodeBase64 };
