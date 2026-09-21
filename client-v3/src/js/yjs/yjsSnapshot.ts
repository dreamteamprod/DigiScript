import * as Y from 'yjs';
import log from 'loglevel';

/**
 * One-way Y.Doc → plain-object snapshot builder. Never write back through these
 * types (hence `Readonly`) — editing writes directly to the live Y.Map/Y.Text via
 * `doc.transact()`, using the same `_id` to find the right node. These are for
 * rendering and for anything that just needs to read current draft content.
 */

export type SnapshotLinePart = Readonly<{
  /** The database identity (or a UUID until saved). A save rewrites it; do not address edits by it. */
  _id: string;
  /** Stable for the life of the part; what edits address it by (see `draftWriter`). */
  _uid: string;
  id: number | null;
  part_index: number;
  character_id: number | null;
  character_group_id: number | null;
  line_text: string;
}>;

export type SnapshotLine = Readonly<{
  _id: string;
  _uid: string;
  id: number | null;
  act_id: number | null;
  scene_id: number | null;
  line_type: number;
  stage_direction_style_id: number | null;
  parts: readonly SnapshotLinePart[];
}>;

/** The Y.Doc field-level sentinel for "no value" is 0, not null (see build_ydoc). */
export function zeroToNull(value: number): number | null {
  return value === 0 ? null : value;
}

export function nullToZero(value: number | null | undefined): number {
  return value == null ? 0 : value;
}

/**
 * Mirrors the server's `_parse_db_id`: a positive integer means an existing DB row;
 * anything else (a UUID string, "0", non-numeric) means a not-yet-saved line/part.
 */
export function parseDbId(rawId: unknown): number | null {
  // Number() (unlike parseInt) requires the *entire* string to be numeric, matching the
  // server's `int(float(str(line_id)))` — parseInt would happily read "3" out of a UUID
  // like "3fa85f64-..." and misreport a brand-new line as an existing DB row.
  const parsed = Number(rawId);
  return Number.isFinite(parsed) && parsed > 0 ? Math.trunc(parsed) : null;
}

/** Read a numeric field, falling back (loudly) on a missing or non-numeric value. */
function readNumber(map: Y.Map<unknown>, key: string, fallback: number): number {
  const value = map.get(key);
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (value !== undefined) {
    log.warn(`yjsSnapshot: expected a number for "${key}", got ${typeof value}; using ${fallback}`);
  }
  return fallback;
}

/**
 * A line/part with no `_id` is corrupt, not new — new ones carry a UUID `_id`. Left
 * alone, `String(undefined)` would yield "undefined", which `parseDbId` reads as
 * null and so passes for a legitimate not-yet-saved line, a path straight into the
 * server's save. Skip and log instead.
 */
function hasId(map: Y.Map<unknown>, kind: string): boolean {
  const id = map.get('_id');
  if (id == null || id === '') {
    log.warn(`yjsSnapshot: skipping ${kind} with no _id`);
    return false;
  }
  return true;
}

/** Drafts from before `_uid` existed only have `_id`, which is then the best identity there is. */
function uidOf(map: Y.Map<unknown>, rawId: string): string {
  const uid = map.get('_uid');
  return uid == null || uid === '' ? rawId : String(uid);
}

function ydocPartToPlain(partMap: Y.Map<unknown>, position: number): SnapshotLinePart {
  const rawId = String(partMap.get('_id'));
  const text = partMap.get('line_text');
  return {
    _id: rawId,
    _uid: uidOf(partMap, rawId),
    id: parseDbId(rawId),
    // Position, not the stored value: two editors appending a part at once both write
    // the same index, and array order is what Yjs converges on (the server does the same).
    part_index: position,
    character_id: zeroToNull(readNumber(partMap, 'character_id', 0)),
    character_group_id: zeroToNull(readNumber(partMap, 'character_group_id', 0)),
    line_text: text instanceof Y.Text ? text.toString() : '',
  };
}

export function ydocLineToPlain(lineMap: Y.Map<unknown>): SnapshotLine {
  const rawId = String(lineMap.get('_id'));
  const partsArr = lineMap.get('parts');
  const parts =
    partsArr instanceof Y.Array
      ? (partsArr.toArray() as Y.Map<unknown>[]).filter((p) => hasId(p, 'part'))
      : [];
  return {
    _id: rawId,
    _uid: uidOf(lineMap, rawId),
    id: parseDbId(rawId),
    act_id: zeroToNull(readNumber(lineMap, 'act_id', 0)),
    scene_id: zeroToNull(readNumber(lineMap, 'scene_id', 0)),
    line_type: readNumber(lineMap, 'line_type', 0),
    stage_direction_style_id: zeroToNull(readNumber(lineMap, 'stage_direction_style_id', 0)),
    parts: parts.map((part, position) => ydocPartToPlain(part, position)),
  };
}

export function ydocPageToPlain(pageArray: Y.Array<Y.Map<unknown>>): SnapshotLine[] {
  return pageArray
    .toArray()
    .filter((line) => hasId(line, 'line'))
    .map(ydocLineToPlain);
}

/** Snapshot every page currently in the doc, keyed by the same string page keys Y.Doc uses. */
export function ydocPagesToPlain(doc: Y.Doc): Record<string, SnapshotLine[]> {
  const pages = doc.getMap('pages') as Y.Map<Y.Array<Y.Map<unknown>>>;
  const result: Record<string, SnapshotLine[]> = {};
  pages.forEach((pageArray, key) => {
    result[key] = ydocPageToPlain(pageArray);
  });
  return result;
}

export function ydocDeletedLineIds(doc: Y.Doc): number[] {
  const arr = doc.getArray('deleted_line_ids') as Y.Array<string>;
  return arr
    .toArray()
    .map((v) => parseDbId(v))
    .filter((v): v is number => v !== null);
}
