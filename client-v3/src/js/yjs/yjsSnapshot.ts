import * as Y from 'yjs';

/**
 * One-way Y.Doc → plain-object snapshot builder. Never write back through these
 * types — editing (Phase 3) writes directly to the live Y.Map/Y.Text via
 * `doc.transact()`, using the same `_id` to find the right node. These are for
 * rendering and for anything that just needs to read current draft content.
 */

export interface SnapshotLinePart {
  _id: string;
  id: number | null;
  part_index: number;
  character_id: number | null;
  character_group_id: number | null;
  line_text: string;
}

export interface SnapshotLine {
  _id: string;
  id: number | null;
  act_id: number | null;
  scene_id: number | null;
  line_type: number;
  stage_direction_style_id: number | null;
  parts: SnapshotLinePart[];
}

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

function ydocPartToPlain(partMap: Y.Map<unknown>): SnapshotLinePart {
  const rawId = String(partMap.get('_id'));
  const text = partMap.get('line_text');
  return {
    _id: rawId,
    id: parseDbId(rawId),
    part_index: (partMap.get('part_index') as number) ?? 0,
    character_id: zeroToNull((partMap.get('character_id') as number) ?? 0),
    character_group_id: zeroToNull((partMap.get('character_group_id') as number) ?? 0),
    line_text: text instanceof Y.Text ? text.toString() : '',
  };
}

export function ydocLineToPlain(lineMap: Y.Map<unknown>): SnapshotLine {
  const rawId = String(lineMap.get('_id'));
  const partsArr = lineMap.get('parts') as Y.Array<Y.Map<unknown>> | undefined;
  return {
    _id: rawId,
    id: parseDbId(rawId),
    act_id: zeroToNull((lineMap.get('act_id') as number) ?? 0),
    scene_id: zeroToNull((lineMap.get('scene_id') as number) ?? 0),
    line_type: (lineMap.get('line_type') as number) ?? 0,
    stage_direction_style_id: zeroToNull((lineMap.get('stage_direction_style_id') as number) ?? 0),
    parts: partsArr ? partsArr.toArray().map(ydocPartToPlain) : [],
  };
}

export function ydocPageToPlain(pageArray: Y.Array<Y.Map<unknown>>): SnapshotLine[] {
  return pageArray.toArray().map(ydocLineToPlain);
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
