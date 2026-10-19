import * as Y from 'yjs';
import log from 'loglevel';
import { bytesToBase64, base64ToBytes } from './base64';

/**
 * Transaction origin used for every update applied to the doc because the server told
 * us to (initial sync, another editor's change, our own change echoed back after save's
 * ID-patch broadcast). The local-update listener below skips this origin so those
 * applies are never re-sent to the server — without this guard a save's ID-patch
 * broadcast (which the server sends to *all* clients, including the one that saved)
 * would loop back out as a fresh YJS_UPDATE. A Symbol, not a string, so no other code
 * using a string origin (e.g. `'local-edit'`) can ever collide with it.
 */
export const SERVER_ORIGIN = Symbol('server');

/** A YJS_SYNC message as the server sends it: full state (0) or a diff reply (2). */
export interface ServerSyncMessage {
  step: 0 | 2;
  payload: string;
}

export interface YjsPayloadMessage {
  payload: string;
}

/** Every message this provider sends; the server dispatches on `OP`. */
export type ClientMessage =
  | { OP: 'JOIN_SCRIPT_ROOM'; DATA: Record<string, never> }
  | { OP: 'LEAVE_SCRIPT_ROOM'; DATA: Record<string, never> }
  | { OP: 'YJS_UPDATE'; DATA: { payload: string } }
  | { OP: 'YJS_AWARENESS'; DATA: { payload: string } }
  // Client→server step 1 is our state vector; step 2 would be a diff we push.
  | { OP: 'YJS_SYNC'; DATA: { step: 1 | 2; payload: string } };

/** Returns whether the message was actually handed to an open socket. */
export type SendFn = (message: ClientMessage) => boolean;

/**
 * Thin wrapper around a Y.Doc that speaks DigiScript's collab WS protocol: base64
 * encode/decode, and routing YJS_SYNC/YJS_UPDATE/YJS_AWARENESS messages in both
 * directions over a caller-supplied `send` function (normally `useWebSocket().sendObj`).
 *
 * Holds no Vue reactivity of its own — callers must keep the `doc` (and this provider)
 * out of any `reactive()`/Pinia state. Vue 3's Proxy walks nested objects the same way
 * Vue 2's `defineProperty` did, and Yjs's internal bookkeeping (`_item`, `_map`,
 * `doc`, ...) breaks under that walk.
 */
export class ScriptDocProvider {
  readonly doc: Y.Doc;

  private readonly send: SendFn;

  private readonly onSendFailed: (() => void) | undefined;

  private destroyed = false;

  private readonly onDocUpdate = (update: Uint8Array, origin: unknown): void => {
    if (origin === SERVER_ORIGIN) {
      return;
    }
    // A dropped local edit must not be silent: the doc keeps the change but the
    // server never sees it, and a later save on another client won't include it.
    if (!this.send({ OP: 'YJS_UPDATE', DATA: { payload: bytesToBase64(update) } })) {
      this.onSendFailed?.();
    }
  };

  constructor(doc: Y.Doc, send: SendFn, onSendFailed?: () => void) {
    this.doc = doc;
    this.send = send;
    this.onSendFailed = onSendFailed;
    this.doc.on('update', this.onDocUpdate);
  }

  destroy(): void {
    this.destroyed = true;
    this.doc.off('update', this.onDocUpdate);
  }

  /** True once destroyed — every method then warns and does nothing rather than touching a dead doc. */
  private isUsable(method: string): boolean {
    if (this.destroyed) {
      log.warn(`ScriptDocProvider: ${method} called after destroy(), ignoring`);
      return false;
    }
    return true;
  }

  join(): boolean {
    if (!this.isUsable('join')) return false;
    return this.send({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });
  }

  leave(): boolean {
    if (!this.isUsable('leave')) return false;
    return this.send({ OP: 'LEAVE_SCRIPT_ROOM', DATA: {} });
  }

  /** Ask the server for a diff since our current state. */
  requestSync(): boolean {
    if (!this.isUsable('requestSync')) return false;
    const stateVector = Y.encodeStateVector(this.doc);
    return this.send({
      OP: 'YJS_SYNC',
      DATA: { step: 1, payload: bytesToBase64(stateVector) },
    });
  }

  /**
   * Apply an incoming YJS_SYNC message (step 0 = full initial state, step 2 = diff).
   * Returns false if nothing was applied (malformed payload, or a step the server should
   * never send) — callers must check this rather than assume success, since a caller
   * that marks itself "synced" unconditionally would report a healthy state over an
   * empty/stale doc.
   */
  applySync(message: ServerSyncMessage): boolean {
    if (!this.isUsable('applySync')) return false;
    // The wire is untyped JSON, so guard the direction asymmetry at runtime too.
    if ((message.step as number) === 1) {
      log.warn('ScriptDocProvider: server sent YJS_SYNC step=1 (client-only direction), ignoring');
      return false;
    }
    return this.applyRemote(message.payload, 'YJS_SYNC');
  }

  /** Apply an incoming YJS_UPDATE message (another editor's change, or our own save's ID-patch). */
  applyUpdate(message: YjsPayloadMessage): boolean {
    if (!this.isUsable('applyUpdate')) return false;
    return this.applyRemote(message.payload, 'YJS_UPDATE');
  }

  private applyRemote(payload: string, context: string): boolean {
    try {
      const update = base64ToBytes(payload);
      Y.applyUpdate(this.doc, update, SERVER_ORIGIN);
      return true;
    } catch (e) {
      log.error(`ScriptDocProvider: failed to apply ${context}`, e);
      return false;
    }
  }

  sendAwareness(update: Uint8Array): boolean {
    if (!this.isUsable('sendAwareness')) return false;
    return this.send({ OP: 'YJS_AWARENESS', DATA: { payload: bytesToBase64(update) } });
  }
}
