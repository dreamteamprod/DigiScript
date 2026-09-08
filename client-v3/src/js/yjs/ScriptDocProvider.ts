import * as Y from 'yjs';
import log from 'loglevel';
import { bytesToBase64, base64ToBytes } from './base64';

/**
 * Transaction origin used for every update applied to the doc because the server told
 * us to (initial sync, another editor's change, our own change echoed back after save's
 * ID-patch broadcast). The local-update listener below skips this origin so those
 * applies are never re-sent to the server — without this guard a save's ID-patch
 * broadcast (which the server sends to *all* clients, including the one that saved)
 * would loop back out as a fresh YJS_UPDATE.
 */
export const SERVER_ORIGIN = 'server';

export interface YjsSyncMessage {
  step: number;
  payload: string;
}

export interface YjsPayloadMessage {
  payload: string;
}

type SendFn = (data: object) => void;

/**
 * Thin wrapper around a Y.Doc that speaks DigiScript's collab WS protocol: base64
 * encode/decode, and routing YJS_SYNC/YJS_UPDATE/YJS_AWARENESS messages in both
 * directions over a caller-supplied `send` function (normally `useWebSocket().sendObj`).
 *
 * Holds no Vue reactivity of its own — callers must keep the `doc` (and this provider)
 * out of any `reactive()`/Pinia state, per the Vue-reactivity-vs-Yjs-internals hazard
 * documented in the plan (Vue's Proxy walks nested Yjs objects the same way Vue 2's
 * `defineProperty` did).
 */
export class ScriptDocProvider {
  readonly doc: Y.Doc;

  private readonly send: SendFn;

  private readonly onDocUpdate = (update: Uint8Array, origin: unknown): void => {
    if (origin === SERVER_ORIGIN) {
      return;
    }
    this.send({ OP: 'YJS_UPDATE', DATA: { payload: bytesToBase64(update) } });
  };

  constructor(doc: Y.Doc, send: SendFn) {
    this.doc = doc;
    this.send = send;
    this.doc.on('update', this.onDocUpdate);
  }

  destroy(): void {
    this.doc.off('update', this.onDocUpdate);
  }

  join(): void {
    this.send({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });
  }

  leave(): void {
    this.send({ OP: 'LEAVE_SCRIPT_ROOM', DATA: {} });
  }

  /** Ask the server for a diff since our current state (used on reconnect). */
  requestSync(): void {
    const stateVector = Y.encodeStateVector(this.doc);
    this.send({
      OP: 'YJS_SYNC',
      DATA: { step: 1, payload: bytesToBase64(stateVector) },
    });
  }

  /** Apply an incoming YJS_SYNC message (step 0 = full initial state, step 2 = diff). */
  applySync(message: YjsSyncMessage): void {
    if (message.step === 1) {
      log.warn('ScriptDocProvider: server sent YJS_SYNC step=1 (client-only direction), ignoring');
      return;
    }
    this.applyRemote(message.payload, 'YJS_SYNC');
  }

  /** Apply an incoming YJS_UPDATE message (another editor's change, or our own save's ID-patch). */
  applyUpdate(message: YjsPayloadMessage): void {
    this.applyRemote(message.payload, 'YJS_UPDATE');
  }

  private applyRemote(payload: string, context: string): void {
    try {
      const update = base64ToBytes(payload);
      Y.applyUpdate(this.doc, update, SERVER_ORIGIN);
    } catch (e) {
      log.error(`ScriptDocProvider: failed to apply ${context}`, e);
    }
  }

  sendAwareness(update: Uint8Array): void {
    this.send({ OP: 'YJS_AWARENESS', DATA: { payload: bytesToBase64(update) } });
  }
}
