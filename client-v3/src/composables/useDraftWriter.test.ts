import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createPinia, setActivePinia } from 'pinia';
import * as Y from 'yjs';
import { useDraftWriter } from './useDraftWriter';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import { useWebSocketStore } from '@/stores/websocket';
import { DraftWriteError } from '@/js/yjs/draftWriter';
import { ydocPagesToPlain } from '@/js/yjs/yjsSnapshot';

vi.mock('@/composables/useWebSocket', () => ({
  useWebSocket: () => ({ sendObj: vi.fn((_data: object) => true), connect: vi.fn() }),
}));
vi.mock('@/js/toast', () => ({
  toast: { info: vi.fn(), error: vi.fn(), success: vi.fn() },
}));

/** Gives the joined draft doc a first (empty) page, as the server would. */
function seedTrailingPage(doc: Y.Doc): void {
  doc.getMap('pages').set('1', new Y.Array<Y.Map<unknown>>());
}

describe('useDraftWriter', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    useWebSocketStore().isConnected = true;
    useWebSocketStore().authenticated = true;
  });

  afterEach(() => {
    useScriptDraftStore()._teardown();
  });

  it('refuses to write when there is no open draft', () => {
    const writer = useDraftWriter();

    expect(() => writer.addLine(1, { lineType: 1 })).toThrow(DraftWriteError);
    expect(() => writer.setPartText(1, 'a', 'b', 'text')).toThrow(/no open draft/);
    try {
      writer.addLine(1, { lineType: 1 });
    } catch (e) {
      expect((e as DraftWriteError).code).toBe('no-draft');
    }
  });

  it('writes to the live draft doc', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    const doc = store.getDraftYdoc()!;
    seedTrailingPage(doc);
    const writer = useDraftWriter();

    const { lineUid, partUid: seedUid } = writer.addLine(1, { lineType: 1, actId: 1, sceneId: 2 });
    const partUid = writer.addPart(1, lineUid, { characterId: 5 })!;
    writer.setPartText(1, lineUid, partUid, 'Hello');

    const line = ydocPagesToPlain(doc)['1'][0];
    expect(line._uid).toBe(lineUid);
    // The line came with a part of its own; the appended one follows it.
    expect(line.parts[0]._uid).toBe(seedUid);
    expect(line.parts[1]).toMatchObject({ _uid: partUid, character_id: 5, line_text: 'Hello' });
  });

  it('follows a draft that was left and re-joined, rather than holding the old doc', () => {
    const store = useScriptDraftStore();
    const writer = useDraftWriter();
    store.joinScriptRoom();
    seedTrailingPage(store.getDraftYdoc()!);
    writer.addLine(1, { lineType: 1 });

    store.leaveScriptRoom();
    expect(() => writer.addLine(1, { lineType: 1 })).toThrow(DraftWriteError);

    store.joinScriptRoom();
    seedTrailingPage(store.getDraftYdoc()!);
    writer.addLine(1, { lineType: 1 });
    expect(ydocPagesToPlain(store.getDraftYdoc()!)['1']).toHaveLength(1);
  });

  it('reaches the live text of a part for caret handling', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    seedTrailingPage(store.getDraftYdoc()!);
    const writer = useDraftWriter();
    const { lineUid, partUid } = writer.addLine(1, { lineType: 1 });
    writer.setPartText(1, lineUid, partUid!, 'abc');

    expect(writer.getPartText(1, lineUid, partUid!)!.toString()).toBe('abc');
  });
});
