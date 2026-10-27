import * as Y from 'yjs';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import * as writer from '@/js/yjs/draftWriter';
import type { LineUid, PartUid } from '@/js/yjs/yjsSnapshot';

/**
 * The draft writer bound to the live draft doc. Components call these with ids and
 * values only; the doc is fetched fresh on every call (see `getDraftYdoc`), so no Yjs
 * object is ever held in component or store state. `transact()` is the one exception
 * to "each call is its own write" — it groups several of the calls below into a
 * single Yjs transaction for a caller that needs them to land as one update (e.g.
 * bulk edit), without ever exposing the `Y.Doc` itself to the caller.
 */
export function useDraftWriter() {
  const store = useScriptDraftStore();

  function doc(): Y.Doc {
    const current = store.getDraftYdoc();
    if (!current) {
      throw new writer.DraftWriteError('There is no open draft to write to', 'no-draft');
    }
    return current;
  }

  return {
    addLine: (page: number, line: writer.NewLine, options?: writer.WriteOptions) =>
      writer.addLine(doc(), page, line, options),
    deleteLine: (page: number, lineUid: LineUid) => writer.deleteLine(doc(), page, lineUid),
    setLineField: (page: number, lineUid: LineUid, field: writer.LineField, value: number | null) =>
      writer.setLineField(doc(), page, lineUid, field, value),
    setLineActScene: (
      page: number,
      lineUid: LineUid,
      actId: number | null,
      sceneId: number | null
    ) => writer.setLineActScene(doc(), page, lineUid, actId, sceneId),
    addPart: (
      page: number,
      lineUid: LineUid,
      part?: writer.NewPart,
      options?: writer.WriteOptions
    ) => writer.addPart(doc(), page, lineUid, part, options),
    removePart: (page: number, lineUid: LineUid, partUid: PartUid) =>
      writer.removePart(doc(), page, lineUid, partUid),
    setPartField: (
      page: number,
      lineUid: LineUid,
      partUid: PartUid,
      field: writer.PartField,
      value: number | null
    ) => writer.setPartField(doc(), page, lineUid, partUid, field, value),
    setPartCharacter: (
      page: number,
      lineUid: LineUid,
      partUid: PartUid,
      characterId: number | null,
      characterGroupId: number | null
    ) => writer.setPartCharacter(doc(), page, lineUid, partUid, characterId, characterGroupId),
    setPartText: (page: number, lineUid: LineUid, partUid: PartUid, text: string) =>
      writer.setPartText(doc(), page, lineUid, partUid, text),
    /** The live text of a part, for `captureSelection`/`resolveSelection`. Do not store it. */
    getPartText: (page: number, lineUid: LineUid, partUid: PartUid) =>
      writer.getPartText(doc(), page, lineUid, partUid),
    /**
     * Run several of the writer calls above as one Yjs transaction (one update
     * on the wire), tagged with the same `LOCAL_EDIT_ORIGIN` each of them
     * already uses individually. Yjs transactions are reentrant, so nesting
     * further writer calls inside `fn` is safe — they join this transaction
     * rather than opening their own. For a multi-line/multi-field operation
     * like bulk edit, which has no single writer function of its own.
     */
    transact: (fn: () => void): void => {
      doc().transact(fn, writer.LOCAL_EDIT_ORIGIN);
    },
  };
}
