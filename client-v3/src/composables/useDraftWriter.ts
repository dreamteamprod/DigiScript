import * as Y from 'yjs';
import { useScriptDraftStore } from '@/stores/scriptDraft';
import * as writer from '@/js/yjs/draftWriter';
import { DraftWriteError } from '@/js/yjs/draftWriter';

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
      throw new DraftWriteError('There is no open draft to write to');
    }
    return current;
  }

  return {
    addLine: (page: number, line: writer.NewLine, options?: writer.WriteOptions) =>
      writer.addLine(doc(), page, line, options),
    deleteLine: (page: number, lineId: string) => writer.deleteLine(doc(), page, lineId),
    setLineField: (page: number, lineId: string, field: writer.LineField, value: number | null) =>
      writer.setLineField(doc(), page, lineId, field, value),
    setLineActScene: (page: number, lineId: string, actId: number | null, sceneId: number | null) =>
      writer.setLineActScene(doc(), page, lineId, actId, sceneId),
    addPart: (page: number, lineId: string, part?: writer.NewPart, options?: writer.WriteOptions) =>
      writer.addPart(doc(), page, lineId, part, options),
    removePart: (page: number, lineId: string, partId: string) =>
      writer.removePart(doc(), page, lineId, partId),
    setPartField: (
      page: number,
      lineId: string,
      partId: string,
      field: writer.PartField,
      value: number | null
    ) => writer.setPartField(doc(), page, lineId, partId, field, value),
    setPartCharacter: (
      page: number,
      lineId: string,
      partId: string,
      characterId: number | null,
      characterGroupId: number | null
    ) => writer.setPartCharacter(doc(), page, lineId, partId, characterId, characterGroupId),
    setPartText: (page: number, lineId: string, partId: string, text: string) =>
      writer.setPartText(doc(), page, lineId, partId, text),
    /** The live text of a part, for `captureSelection`/`resolveSelection`. Do not store it. */
    getPartText: (page: number, lineId: string, partId: string) =>
      writer.getPartText(doc(), page, lineId, partId),
  };
}
