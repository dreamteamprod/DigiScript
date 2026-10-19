import * as Y from 'yjs';
import { LINE_TYPES, type LineType } from '@/constants/lineTypes';
import { nullToZero, parseDbId, uidOf } from './yjsSnapshot';
import { applyTextDiff } from './ytextDiff';

/**
 * Every edit the script editor makes to the shared draft.
 *
 * Lines and parts are addressed by their `_uid`, never by position: another editor's
 * insert or delete shifts every index but not a `_uid`. `_uid` is assigned when a line
 * or part is created and never rewritten. That is why it, not `_id`, is the address:
 * `_id` is the *database* identity, which a save rewrites in place (UUID → DB id for
 * new rows, old → new DB id for changed ones), so anything holding an `_id` would
 * lose its target the moment a save lands. Callers pass the page a line is on, so a
 * write is a lookup in one page rather than a scan of the whole script.
 *
 * Contract for a target that has vanished: with several editors that is a normal
 * condition (another editor deleted the line you were typing in), so the writers do not
 * throw for it. They return `false` (or `null` for functions that return an id), and
 * the caller decides what to tell the user. `setPartText` returns a string
 * (`'changed' | 'unchanged' | 'gone'`), all truthy, so never test it with `!`. `DraftWriteError`
 * (with a `code`) is reserved for bugs or a broken draft: no open draft, a page that does
 * not exist, or a part given both a character and a group.
 *
 * Each function is at most one Yjs transaction (so one update on the wire), tagged
 * with `LOCAL_EDIT_ORIGIN`. Nothing here holds a Yjs object between calls — they take
 * the `Y.Doc` and look things up fresh, so callers never keep a `Y.Map`/`Y.Text` in
 * reactive state.
 *
 * The structure written must stay identical to what the server's `build_ydoc` builds
 * and `extract_lines_from_ydoc` reads (see the cross-language fixture test).
 */

/** Transaction origin for edits made in this browser. */
export const LOCAL_EDIT_ORIGIN = 'local-edit';

/** Why a write was refused, so callers can branch without matching message strings. */
export type DraftWriteErrorCode = 'no-draft' | 'page-missing' | 'invalid';

export class DraftWriteError extends Error {
  readonly code: DraftWriteErrorCode;

  constructor(message: string, code: DraftWriteErrorCode = 'invalid') {
    super(message);
    this.name = 'DraftWriteError';
    this.code = code;
  }
}

export type LineField = 'act_id' | 'scene_id' | 'stage_direction_style_id';
export type PartField = 'character_id' | 'character_group_id';

export interface WriteOptions {
  /** Generates the `_uid` (and initial `_id`) for a new line or part. Injectable so tests are deterministic. */
  newId?: () => string;
}

const defaultNewId = (): string => crypto.randomUUID();

type LineMap = Y.Map<unknown>;
type PartMap = Y.Map<unknown>;
type PageArray = Y.Array<LineMap>;

/**
 * Pages are created by the server (it always keeps the doc ending in an empty page), never by a
 * client: if two editors each created the same new page, Yjs would keep only one of the
 * two arrays and silently discard the other editor's lines. Writing into an existing
 * array merges cleanly, so a missing page is an error here, not something to create.
 */
function getPage(doc: Y.Doc, page: number): PageArray {
  const array = doc.getMap('pages').get(String(page));
  if (!(array instanceof Y.Array)) {
    throw new DraftWriteError(`Page ${page} does not exist in the draft`, 'page-missing');
  }
  return array as PageArray;
}

function findLine(
  doc: Y.Doc,
  page: number,
  lineUid: string
): { line: LineMap; index: number } | null {
  const array = getPage(doc, page);
  for (let index = 0; index < array.length; index += 1) {
    const line = array.get(index);
    if (uidOf(line) === lineUid) return { line, index };
  }
  return null;
}

function getParts(line: LineMap): Y.Array<PartMap> {
  const parts = line.get('parts');
  if (!(parts instanceof Y.Array)) {
    throw new DraftWriteError('Line has no parts array', 'invalid');
  }
  return parts as Y.Array<PartMap>;
}

function findPart(
  doc: Y.Doc,
  page: number,
  lineUid: string,
  partUid: string
): { part: PartMap; index: number; parts: Y.Array<PartMap> } | null {
  const found = findLine(doc, page, lineUid);
  if (!found) return null;
  const parts = getParts(found.line);
  for (let index = 0; index < parts.length; index += 1) {
    const part = parts.get(index);
    if (uidOf(part) === partUid) return { part, index, parts };
  }
  return null;
}

/**
 * `part_index` is written for the benefit of readers of the raw doc, but it is advisory:
 * two editors appending a part at once both write the same value, so the server (and
 * `yjsSnapshot`) derive a part's index from its position in the array instead.
 */
function makePartMap(
  uid: string,
  partIndex: number,
  characterId: number | null,
  characterGroupId: number | null
): PartMap {
  const part = new Y.Map<unknown>();
  part.set('_id', uid);
  part.set('_uid', uid);
  part.set('part_index', partIndex);
  part.set('character_id', nullToZero(characterId));
  part.set('character_group_id', nullToZero(characterGroupId));
  part.set('line_text', new Y.Text(''));
  return part;
}

/**
 * A part has a character or a character group, never both. Enforced here rather than
 * trusted to callers: the server would otherwise save a part claiming both.
 */
function assertNotBoth(characterId: number | null, characterGroupId: number | null): void {
  if (characterId != null && characterGroupId != null) {
    throw new DraftWriteError('A part cannot have both a character and a character group');
  }
}

/** Line types that carry parts; cue and spacing lines must have none (the server rejects them). */
const PART_LINE_TYPES: readonly LineType[] = [LINE_TYPES.DIALOGUE, LINE_TYPES.STAGE_DIRECTION];

export interface NewLine {
  lineType: LineType;
  actId?: number | null;
  sceneId?: number | null;
  stageDirectionStyleId?: number | null;
  /** Insert position within the page; defaults to the end. */
  index?: number;
  /** Seeded into the line's first part (only for line types that have parts). */
  part?: NewPart;
}

export interface NewLineIds {
  lineUid: string;
  /** The line's first part, or null for a line type that has none (cue, spacing). */
  partUid: string | null;
}

/**
 * Add a line to an existing page and return the `_uid`s of the line and of its first
 * part. A dialogue or stage-direction line is created *with* one empty part in the same
 * transaction: a separate `addPart` call would let a peer, or a save, observe such a line
 * with no parts. Cue and spacing lines have no parts (the server rejects them
 * otherwise), so none is created and `partUid` is null.
 */
export function addLine(
  doc: Y.Doc,
  page: number,
  line: NewLine,
  { newId = defaultNewId }: WriteOptions = {}
): NewLineIds {
  const lineUid = newId();
  const hasParts = PART_LINE_TYPES.includes(line.lineType);
  if (line.part && !hasParts) {
    throw new DraftWriteError(`Line type ${line.lineType} cannot have parts`);
  }
  const partUid = hasParts ? newId() : null;
  const seed = line.part ?? {};
  assertNotBoth(seed.characterId ?? null, seed.characterGroupId ?? null);
  const requestedIndex = Number.isFinite(line.index) ? (line.index as number) : undefined;
  doc.transact(() => {
    const array = getPage(doc, page);
    const map: LineMap = new Y.Map<unknown>();
    map.set('_id', lineUid);
    map.set('_uid', lineUid);
    map.set('act_id', nullToZero(line.actId));
    map.set('scene_id', nullToZero(line.sceneId));
    map.set('line_type', line.lineType);
    map.set('stage_direction_style_id', nullToZero(line.stageDirectionStyleId));
    const parts = new Y.Array<PartMap>();
    map.set('parts', parts);
    array.insert(Math.min(Math.max(requestedIndex ?? array.length, 0), array.length), [map]);
    if (partUid !== null) {
      // Integrated into the doc first, then filled (a Y type must be attached to be written).
      parts.push([
        makePartMap(partUid, 0, seed.characterId ?? null, seed.characterGroupId ?? null),
      ]);
    }
  }, LOCAL_EDIT_ORIGIN);
  return { lineUid, partUid };
}

/**
 * Remove a line and record its current `_id` in `deleted_line_ids`, so the server deletes
 * the row on save. The id is recorded even when it is still a UUID: this client may just
 * not have received the id patch of a save that already persisted the line, and the
 * server remembers those rewrites and resolves the entry. For a line that was never
 * saved the entry is harmless (skipped, then wiped by the next save). Returns false if
 * the line was already gone.
 */
export function deleteLine(doc: Y.Doc, page: number, lineUid: string): boolean {
  let deleted = false;
  doc.transact(() => {
    const found = findLine(doc, page, lineUid);
    if (!found) return;
    const id = found.line.get('_id');
    getPage(doc, page).delete(found.index, 1);
    // A missing `_id` (corrupt line) is not an id: `String(undefined)` would be recorded.
    if (typeof id === 'string' && id !== '') {
      doc.getArray<string>('deleted_line_ids').push([id]);
    }
    deleted = true;
  }, LOCAL_EDIT_ORIGIN);
  return deleted;
}

export function setLineField(
  doc: Y.Doc,
  page: number,
  lineUid: string,
  field: LineField,
  value: number | null
): boolean {
  let applied = false;
  doc.transact(() => {
    const found = findLine(doc, page, lineUid);
    if (!found) return;
    found.line.set(field, nullToZero(value));
    applied = true;
  }, LOCAL_EDIT_ORIGIN);
  return applied;
}

/** Set act and scene together as one update (they are always changed as a pair). */
export function setLineActScene(
  doc: Y.Doc,
  page: number,
  lineUid: string,
  actId: number | null,
  sceneId: number | null
): boolean {
  let applied = false;
  doc.transact(() => {
    const found = findLine(doc, page, lineUid);
    if (!found) return;
    found.line.set('act_id', nullToZero(actId));
    found.line.set('scene_id', nullToZero(sceneId));
    applied = true;
  }, LOCAL_EDIT_ORIGIN);
  return applied;
}

export interface NewPart {
  characterId?: number | null;
  characterGroupId?: number | null;
}

/** Append an empty part to a line and return its `_uid`, or null if the line is gone. */
export function addPart(
  doc: Y.Doc,
  page: number,
  lineUid: string,
  part: NewPart = {},
  { newId = defaultNewId }: WriteOptions = {}
): string | null {
  const characterId = part.characterId ?? null;
  const characterGroupId = part.characterGroupId ?? null;
  assertNotBoth(characterId, characterGroupId);
  const uid = newId();
  let added = false;
  doc.transact(() => {
    const found = findLine(doc, page, lineUid);
    if (!found) return;
    const parts = getParts(found.line);
    parts.push([makePartMap(uid, parts.length, characterId, characterGroupId)]);
    added = true;
  }, LOCAL_EDIT_ORIGIN);
  return added ? uid : null;
}

/**
 * Remove a part. The rest are not renumbered: a part's index is its position, which a
 * removal already shifts, and renumbering from one editor's view is exactly what
 * concurrent edits would get wrong. Returns false if the part was already gone.
 */
export function removePart(doc: Y.Doc, page: number, lineUid: string, partUid: string): boolean {
  let removed = false;
  doc.transact(() => {
    const found = findPart(doc, page, lineUid, partUid);
    if (!found) return;
    found.parts.delete(found.index, 1);
    removed = true;
  }, LOCAL_EDIT_ORIGIN);
  return removed;
}

/**
 * Set one of a part's two character fields. Setting a value clears the other field, so
 * the "one or the other" rule holds whichever is set; use `setPartCharacter` to set both
 * explicitly.
 */
export function setPartField(
  doc: Y.Doc,
  page: number,
  lineUid: string,
  partUid: string,
  field: PartField,
  value: number | null
): boolean {
  let applied = false;
  doc.transact(() => {
    const found = findPart(doc, page, lineUid, partUid);
    if (!found) return;
    found.part.set(field, nullToZero(value));
    if (value != null) {
      found.part.set(
        field === 'character_id' ? 'character_group_id' : 'character_id',
        nullToZero(null)
      );
    }
    applied = true;
  }, LOCAL_EDIT_ORIGIN);
  return applied;
}

/** Set character and group together — a part has one or the other, never both (throws if both). */
export function setPartCharacter(
  doc: Y.Doc,
  page: number,
  lineUid: string,
  partUid: string,
  characterId: number | null,
  characterGroupId: number | null
): boolean {
  assertNotBoth(characterId, characterGroupId);
  let applied = false;
  doc.transact(() => {
    const found = findPart(doc, page, lineUid, partUid);
    if (!found) return;
    found.part.set('character_id', nullToZero(characterId));
    found.part.set('character_group_id', nullToZero(characterGroupId));
    applied = true;
  }, LOCAL_EDIT_ORIGIN);
  return applied;
}

/**
 * The live `Y.Text` of a part, for binding an input (see `applyTextDiff`). Do not store
 * it. Null if the part is gone.
 */
export function getPartText(
  doc: Y.Doc,
  page: number,
  lineUid: string,
  partUid: string
): Y.Text | null {
  const found = findPart(doc, page, lineUid, partUid);
  if (!found) return null;
  const text = found.part.get('line_text');
  if (!(text instanceof Y.Text)) {
    throw new DraftWriteError(`Part ${partUid} has no text`);
  }
  return text;
}

export type SetTextResult = 'changed' | 'unchanged' | 'gone';

/**
 * Make a part's text equal `text` using the minimal edit. `'gone'` means the part no
 * longer exists (another editor removed it), which a keystroke handler must tell apart
 * from `'unchanged'` or the typed input is silently dropped.
 */
export function setPartText(
  doc: Y.Doc,
  page: number,
  lineUid: string,
  partUid: string,
  text: string
): SetTextResult {
  const ytext = getPartText(doc, page, lineUid, partUid);
  if (!ytext) return 'gone';
  return applyTextDiff(ytext, text, LOCAL_EDIT_ORIGIN) ? 'changed' : 'unchanged';
}
