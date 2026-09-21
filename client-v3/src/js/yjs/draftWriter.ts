import * as Y from 'yjs';
import { nullToZero, parseDbId } from './yjsSnapshot';
import { applyTextDiff } from './ytextDiff';

/**
 * Every edit the script editor makes to the shared draft.
 *
 * Lines and parts are addressed by their `_id` (a UUID until the first save, then the
 * DB id), never by position: another editor's insert or delete shifts every index but
 * not an `_id`. Callers pass the page a line is on, so a write is a lookup in one page
 * rather than a scan of the whole script on every keystroke.
 *
 * Each function is exactly one Yjs transaction (so one update on the wire), tagged
 * with `LOCAL_EDIT_ORIGIN`. Nothing here holds a Yjs object between calls — they take
 * the `Y.Doc` and look things up fresh, so callers never keep a `Y.Map`/`Y.Text` in
 * reactive state.
 *
 * The structure written must stay identical to what the server's `build_ydoc` builds
 * and `extract_lines_from_ydoc` reads (see the cross-language fixture test).
 */

/** Transaction origin for edits made in this browser. */
export const LOCAL_EDIT_ORIGIN = 'local-edit';

export class DraftWriteError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'DraftWriteError';
  }
}

export type LineField = 'act_id' | 'scene_id' | 'stage_direction_style_id';
export type PartField = 'character_id' | 'character_group_id';

export interface WriteOptions {
  /** Generates the `_id` for a new line or part. Injectable so tests are deterministic. */
  newId?: () => string;
}

const defaultNewId = (): string => crypto.randomUUID();

type LineMap = Y.Map<unknown>;
type PageArray = Y.Array<LineMap>;

/**
 * Pages are created by the server (it always keeps one empty trailing page), never by a
 * client: if two editors each created the same new page, Yjs would keep only one of the
 * two arrays and silently discard the other editor's lines. Writing into an existing
 * array merges cleanly, so a missing page is an error here, not something to create.
 */
function getPage(doc: Y.Doc, page: number): PageArray {
  const array = doc.getMap('pages').get(String(page));
  if (!(array instanceof Y.Array)) {
    throw new DraftWriteError(`Page ${page} does not exist in the draft`);
  }
  return array as PageArray;
}

function findLine(doc: Y.Doc, page: number, lineId: string): { line: LineMap; index: number } {
  const array = getPage(doc, page);
  for (let index = 0; index < array.length; index += 1) {
    const line = array.get(index);
    if (String(line.get('_id')) === lineId) return { line, index };
  }
  throw new DraftWriteError(`Line ${lineId} not found on page ${page}`);
}

function getParts(line: LineMap): Y.Array<Y.Map<unknown>> {
  const parts = line.get('parts');
  if (!(parts instanceof Y.Array)) {
    throw new DraftWriteError('Line has no parts array');
  }
  return parts as Y.Array<Y.Map<unknown>>;
}

function findPart(
  doc: Y.Doc,
  page: number,
  lineId: string,
  partId: string
): { part: Y.Map<unknown>; index: number; parts: Y.Array<Y.Map<unknown>> } {
  const parts = getParts(findLine(doc, page, lineId).line);
  for (let index = 0; index < parts.length; index += 1) {
    const part = parts.get(index);
    if (String(part.get('_id')) === partId) return { part, index, parts };
  }
  throw new DraftWriteError(`Part ${partId} not found on line ${lineId}`);
}

function makePartMap(
  partId: string,
  partIndex: number,
  characterId: number | null,
  characterGroupId: number | null
): Y.Map<unknown> {
  const part = new Y.Map<unknown>();
  part.set('_id', partId);
  part.set('part_index', partIndex);
  part.set('character_id', nullToZero(characterId));
  part.set('character_group_id', nullToZero(characterGroupId));
  part.set('line_text', new Y.Text(''));
  return part;
}

export interface NewLine {
  lineType: number;
  actId?: number | null;
  sceneId?: number | null;
  stageDirectionStyleId?: number | null;
  /** Insert position within the page; defaults to the end. */
  index?: number;
}

/** Add an empty line to an existing page and return its new `_id`. */
export function addLine(
  doc: Y.Doc,
  page: number,
  line: NewLine,
  { newId = defaultNewId }: WriteOptions = {}
): string {
  const id = newId();
  doc.transact(() => {
    const array = getPage(doc, page);
    const map: LineMap = new Y.Map<unknown>();
    map.set('_id', id);
    map.set('act_id', nullToZero(line.actId));
    map.set('scene_id', nullToZero(line.sceneId));
    map.set('line_type', line.lineType);
    map.set('stage_direction_style_id', nullToZero(line.stageDirectionStyleId));
    map.set('parts', new Y.Array<Y.Map<unknown>>());
    array.insert(Math.min(Math.max(line.index ?? array.length, 0), array.length), [map]);
  }, LOCAL_EDIT_ORIGIN);
  return id;
}

/**
 * Remove a line. A line that already exists in the DB is also recorded in
 * `deleted_line_ids` so the server deletes it on save; a line that was never saved
 * (UUID `_id`) simply disappears.
 */
export function deleteLine(doc: Y.Doc, page: number, lineId: string): void {
  doc.transact(() => {
    const { index } = findLine(doc, page, lineId);
    getPage(doc, page).delete(index, 1);
    if (parseDbId(lineId) !== null) {
      doc.getArray<string>('deleted_line_ids').push([lineId]);
    }
  }, LOCAL_EDIT_ORIGIN);
}

export function setLineField(
  doc: Y.Doc,
  page: number,
  lineId: string,
  field: LineField,
  value: number | null
): void {
  doc.transact(() => {
    findLine(doc, page, lineId).line.set(field, nullToZero(value));
  }, LOCAL_EDIT_ORIGIN);
}

/** Set act and scene together as one update (they are always changed as a pair). */
export function setLineActScene(
  doc: Y.Doc,
  page: number,
  lineId: string,
  actId: number | null,
  sceneId: number | null
): void {
  doc.transact(() => {
    const { line } = findLine(doc, page, lineId);
    line.set('act_id', nullToZero(actId));
    line.set('scene_id', nullToZero(sceneId));
  }, LOCAL_EDIT_ORIGIN);
}

export interface NewPart {
  characterId?: number | null;
  characterGroupId?: number | null;
}

/** Append an empty part to a line and return its new `_id`. */
export function addPart(
  doc: Y.Doc,
  page: number,
  lineId: string,
  part: NewPart = {},
  { newId = defaultNewId }: WriteOptions = {}
): string {
  const id = newId();
  doc.transact(() => {
    const parts = getParts(findLine(doc, page, lineId).line);
    parts.push([
      makePartMap(id, parts.length, part.characterId ?? null, part.characterGroupId ?? null),
    ]);
  }, LOCAL_EDIT_ORIGIN);
  return id;
}

/** Remove a part and renumber the rest 0..n-1, as the classic editor does. */
export function removePart(doc: Y.Doc, page: number, lineId: string, partId: string): void {
  doc.transact(() => {
    const { index, parts } = findPart(doc, page, lineId, partId);
    parts.delete(index, 1);
    for (let i = index; i < parts.length; i += 1) {
      parts.get(i).set('part_index', i);
    }
  }, LOCAL_EDIT_ORIGIN);
}

export function setPartField(
  doc: Y.Doc,
  page: number,
  lineId: string,
  partId: string,
  field: PartField,
  value: number | null
): void {
  doc.transact(() => {
    findPart(doc, page, lineId, partId).part.set(field, nullToZero(value));
  }, LOCAL_EDIT_ORIGIN);
}

/** Set character and group together — a part has one or the other, never both. */
export function setPartCharacter(
  doc: Y.Doc,
  page: number,
  lineId: string,
  partId: string,
  characterId: number | null,
  characterGroupId: number | null
): void {
  doc.transact(() => {
    const { part } = findPart(doc, page, lineId, partId);
    part.set('character_id', nullToZero(characterId));
    part.set('character_group_id', nullToZero(characterGroupId));
  }, LOCAL_EDIT_ORIGIN);
}

/** The live `Y.Text` of a part, for binding an input (see `applyTextDiff`). Do not store it. */
export function getPartText(doc: Y.Doc, page: number, lineId: string, partId: string): Y.Text {
  const text = findPart(doc, page, lineId, partId).part.get('line_text');
  if (!(text instanceof Y.Text)) {
    throw new DraftWriteError(`Part ${partId} has no text`);
  }
  return text;
}

/** Make a part's text equal `text` using the minimal edit. Returns whether anything changed. */
export function setPartText(
  doc: Y.Doc,
  page: number,
  lineId: string,
  partId: string,
  text: string
): boolean {
  return applyTextDiff(getPartText(doc, page, lineId, partId), text, LOCAL_EDIT_ORIGIN);
}
