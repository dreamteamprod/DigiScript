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
  });

  it('writes to the live draft doc', () => {
    const store = useScriptDraftStore();
    store.joinScriptRoom();
    const doc = store.getDraftYdoc()!;
    seedTrailingPage(doc);
    const writer = useDraftWriter();

    const lineId = writer.addLine(1, { lineType: 1, actId: 1, sceneId: 2 });
    const partId = writer.addPart(1, lineId, { characterId: 5 });
    writer.setPartText(1, lineId, partId, 'Hello');

    const line = ydocPagesToPlain(doc)['1'][0];
    expect(line._id).toBe(lineId);
    expect(line.parts[0]).toMatchObject({ _id: partId, character_id: 5, line_text: 'Hello' });
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
    const lineId = writer.addLine(1, { lineType: 1 });
    const partId = writer.addPart(1, lineId);
    writer.setPartText(1, lineId, partId, 'abc');

    expect(writer.getPartText(1, lineId, partId).toString()).toBe('abc');
  });
});
