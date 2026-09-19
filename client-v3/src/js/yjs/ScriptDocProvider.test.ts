import { describe, it, expect, vi } from 'vitest';
import * as Y from 'yjs';
import { ScriptDocProvider, type ServerSyncMessage } from './ScriptDocProvider';
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

    expect(provider.applyUpdate({ payload: bytesToBase64(remoteUpdate) })).toBe(true);

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

    expect(provider.applySync({ step: 0, payload: bytesToBase64(fullState) })).toBe(true);

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

    expect(provider.applySync({ step: 2, payload: bytesToBase64(diff) })).toBe(true);

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

    expect(provider.applySync({ step: 1, payload: '' } as unknown as ServerSyncMessage)).toBe(
      false
    );
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

  it('swallows a corrupt payload instead of throwing, and reports failure', () => {
    const doc = new Y.Doc();
    const send = vi.fn();
    const provider = new ScriptDocProvider(doc, send);

    let result: boolean | undefined;
    expect(() => {
      result = provider.applyUpdate({ payload: 'not-valid-base64-yjs-data!!' });
    }).not.toThrow();
    expect(result).toBe(false);

    provider.destroy();
  });

  it('reports a failed send of a local edit through onSendFailed', () => {
    const doc = new Y.Doc();
    const send = vi.fn(() => false);
    const onSendFailed = vi.fn();
    const provider = new ScriptDocProvider(doc, send, onSendFailed);

    doc.transact(() => {
      doc.getMap('meta').set('k', 1);
    }, 'local-edit');

    expect(onSendFailed).toHaveBeenCalledTimes(1);

    provider.destroy();
  });

  it('does not report a failure when the send succeeds', () => {
    const doc = new Y.Doc();
    const onSendFailed = vi.fn();
    const provider = new ScriptDocProvider(
      doc,
      vi.fn(() => true),
      onSendFailed
    );

    doc.transact(() => {
      doc.getMap('meta').set('k', 1);
    }, 'local-edit');

    expect(onSendFailed).not.toHaveBeenCalled();

    provider.destroy();
  });

  it('a string origin of "server" is a normal local edit — only the private sentinel is exempt from sending', () => {
    const doc = new Y.Doc();
    const send = vi.fn(() => true);
    const provider = new ScriptDocProvider(doc, send);

    doc.transact(() => {
      doc.getMap('meta').set('k', 1);
    }, 'server');

    expect(send).toHaveBeenCalledTimes(1);

    provider.destroy();
  });

  it('every method refuses to act after destroy() and reports that it did nothing', () => {
    const doc = new Y.Doc();
    const send = vi.fn(() => true);
    const provider = new ScriptDocProvider(doc, send);
    provider.destroy();
    const update = bytesToBase64(Y.encodeStateAsUpdate(new Y.Doc()));

    expect(provider.join()).toBe(false);
    expect(provider.leave()).toBe(false);
    expect(provider.requestSync()).toBe(false);
    expect(provider.sendAwareness(new Uint8Array([1]))).toBe(false);
    expect(provider.applyUpdate({ payload: update })).toBe(false);
    expect(provider.applySync({ step: 0, payload: update })).toBe(false);
    expect(send).not.toHaveBeenCalled();
  });

  it('rejects valid base64 that is not a valid Yjs update', () => {
    const doc = new Y.Doc();
    const provider = new ScriptDocProvider(
      doc,
      vi.fn(() => true)
    );

    expect(
      provider.applyUpdate({ payload: bytesToBase64(new Uint8Array([255, 255, 255, 255, 9])) })
    ).toBe(false);

    provider.destroy();
  });

  it('rejects a truncated Yjs update without changing the doc', () => {
    const remote = new Y.Doc();
    remote.transact(() => {
      remote.getMap('meta').set('revision_id', 5);
      remote.getMap('meta').set('other', 'a fairly long string value to truncate');
    }, 'local-edit');
    const full = Y.encodeStateAsUpdate(remote);
    const doc = new Y.Doc();
    const provider = new ScriptDocProvider(
      doc,
      vi.fn(() => true)
    );

    const applied = provider.applyUpdate({
      payload: bytesToBase64(full.slice(0, full.length - 8)),
    });

    expect(applied).toBe(false);
    expect(doc.getMap('meta').get('revision_id')).toBeUndefined();

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
