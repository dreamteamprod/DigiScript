import * as Y from 'yjs';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import * as writer from '@/js/yjs/draftWriter';

/**
 * The draft writer bound to the live draft doc. Components call these with ids and
 * values only; the doc is fetched fresh on every call (see `getDraftYdoc`), so no Yjs
 * object is ever held in component or store state.
 */
export function useDraftWriter() {
  const store = useScriptDraftStore();

  function doc(): Y.Doc {
    const current = store.getDraftYdoc();
    if (!current) {
      throw new writer.DraftWriteError('There is no open draft to write to');
    }
    return current;
  }

  return {
    addLine: (page: number, line: writer.NewLine, options?: writer.WriteOptions) =>
      writer.addLine(doc(), page, line, options),
    deleteLine: (page: number, lineUid: string) => writer.deleteLine(doc(), page, lineUid),
    setLineField: (page: number, lineUid: string, field: writer.LineField, value: number | null) =>
      writer.setLineField(doc(), page, lineUid, field, value),
    setLineActScene: (
      page: number,
      lineUid: string,
      actId: number | null,
      sceneId: number | null
    ) => writer.setLineActScene(doc(), page, lineUid, actId, sceneId),
    addPart: (
      page: number,
      lineUid: string,
      part?: writer.NewPart,
      options?: writer.WriteOptions
    ) => writer.addPart(doc(), page, lineUid, part, options),
    removePart: (page: number, lineUid: string, partUid: string) =>
      writer.removePart(doc(), page, lineUid, partUid),
    setPartField: (
      page: number,
      lineUid: string,
      partUid: string,
      field: writer.PartField,
      value: number | null
    ) => writer.setPartField(doc(), page, lineUid, partUid, field, value),
    setPartCharacter: (
      page: number,
      lineUid: string,
      partUid: string,
      characterId: number | null,
      characterGroupId: number | null
    ) => writer.setPartCharacter(doc(), page, lineUid, partUid, characterId, characterGroupId),
    setPartText: (page: number, lineUid: string, partUid: string, text: string) =>
      writer.setPartText(doc(), page, lineUid, partUid, text),
    /** The live text of a part, for `captureSelection`/`resolveSelection`. Do not store it. */
    getPartText: (page: number, lineUid: string, partUid: string) =>
      writer.getPartText(doc(), page, lineUid, partUid),
  };
}
