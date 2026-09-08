import { describe, it, expect, vi } from 'vitest';
import * as Y from 'yjs';
import { ScriptDocProvider } from './ScriptDocProvider';
import { bytesToBase64 } from './base64';

describe('ScriptDocProvider', () => {
  it('sends a YJS_UPDATE for a local transaction', () => {
    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    doc.transact(() => {
      doc.getMap('meta').set('revision_id', 1);
    }, 'local-edit');

    expect(send).toHaveBeenCalledTimes(1);
    const call = send.mock.calls[0][0] as { OP: string; DATA: { payload: string } };
    expect(call.OP).toBe('YJS_UPDATE');
    expect(typeof call.DATA.payload).toBe('string');

    provider.destroy();
  });

  it('does not echo an update applied via applyUpdate back to the server', () => {
    // Build the "remote" change on a second doc, exactly as the server would relay it.
    const remoteDoc = new Y.Doc();
    remoteDoc.transact(() => {
      remoteDoc.getMap('meta').set('revision_id', 42);
    }, 'local-edit');
    const remoteUpdate = Y.encodeStateAsUpdate(remoteDoc);

    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    provider.applyUpdate({ payload: bytesToBase64(remoteUpdate) });

    expect(send).not.toHaveBeenCalled();
    expect(doc.getMap('meta').get('revision_id')).toBe(42);

    provider.destroy();
  });

  it('does not echo the initial full-state sync (step 0) back to the server', () => {
    const remoteDoc = new Y.Doc();
    remoteDoc.transact(() => {
      remoteDoc.getMap('meta').set('revision_id', 7);
    }, 'local-edit');
    const fullState = Y.encodeStateAsUpdate(remoteDoc);

    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    provider.applySync({ step: 0, payload: bytesToBase64(fullState) });

    expect(send).not.toHaveBeenCalled();
    expect(doc.getMap('meta').get('revision_id')).toBe(7);

    provider.destroy();
  });

  it('does not echo a step=2 diff sync back to the server', () => {
    const remoteDoc = new Y.Doc();
    remoteDoc.transact(() => {
      remoteDoc.getMap('meta').set('revision_id', 99);
    }, 'local-edit');
    const diff = Y.encodeStateAsUpdate(remoteDoc);

    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    provider.applySync({ step: 2, payload: bytesToBase64(diff) });

    expect(send).not.toHaveBeenCalled();
    expect(doc.getMap('meta').get('revision_id')).toBe(99);

    provider.destroy();
  });

  it('still forwards a genuine local edit made after a remote apply', () => {
    const remoteDoc = new Y.Doc();
    remoteDoc.transact(() => {
      remoteDoc.getMap('meta').set('revision_id', 1);
    }, 'local-edit');

    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    provider.applyUpdate({ payload: bytesToBase64(Y.encodeStateAsUpdate(remoteDoc)) });
    expect(send).not.toHaveBeenCalled();

    doc.transact(() => {
      doc.getMap('meta').set('last_saved_at', 'now');
    }, 'local-edit');

    expect(send).toHaveBeenCalledTimes(1);

    provider.destroy();
  });

  it('sends JOIN_SCRIPT_ROOM / LEAVE_SCRIPT_ROOM with the expected shape', () => {
    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    provider.join();
    expect(send).toHaveBeenCalledWith({ OP: 'JOIN_SCRIPT_ROOM', DATA: {} });

    provider.leave();
    expect(send).toHaveBeenCalledWith({ OP: 'LEAVE_SCRIPT_ROOM', DATA: {} });

    provider.destroy();
  });

  it('requestSync sends our state vector as a step=1 YJS_SYNC', () => {
    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    provider.requestSync();

    expect(send).toHaveBeenCalledTimes(1);
    const call = send.mock.calls[0][0] as {
      OP: string;
      DATA: { step: number; payload: string };
    };
    expect(call.OP).toBe('YJS_SYNC');
    expect(call.DATA.step).toBe(1);

    provider.destroy();
  });

  it('ignores a step=1 YJS_SYNC received from the server (client-only direction)', () => {
    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    expect(() => provider.applySync({ step: 1, payload: '' })).not.toThrow();
    expect(send).not.toHaveBeenCalled();

    provider.destroy();
  });

  it('sends awareness updates as base64', () => {
    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    provider.sendAwareness(new Uint8Array([1, 2, 3]));

    expect(send).toHaveBeenCalledWith({
      OP: 'YJS_AWARENESS',
      DATA: { payload: bytesToBase64(new Uint8Array([1, 2, 3])) },
    });

    provider.destroy();
  });

  it('swallows a corrupt payload instead of throwing', () => {
    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    expect(() => provider.applyUpdate({ payload: 'not-valid-base64-yjs-data!!' })).not.toThrow();

    provider.destroy();
  });

  it('destroy() stops forwarding local updates', () => {
    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    provider.destroy();
    doc.transact(() => {
      doc.getMap('meta').set('revision_id', 1);
    }, 'local-edit');

    expect(send).not.toHaveBeenCalled();
  });
});
