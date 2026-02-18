/**
 * Bridge utilities for Y.Doc ↔ TMP_SCRIPT format conversion.
 *
 * Y.Doc is the source of truth during collaborative editing. TMP_SCRIPT is a
 * read-only view cache populated one-way from Y.Doc via observers.
 * Components write directly to Y.Map/Y.Text; this module provides:
 *   - Y.Doc → plain object conversion (for the TMP_SCRIPT view cache)
 *   - Structural helpers (add/delete lines in Y.Doc)
 *   - Sentinel conversion (nullToZero / zeroToNull)
 *
 * Schema differences between Y.Doc and TMP_SCRIPT:
 *   - `_id` instead of `id`
 *   - `parts` instead of `line_parts`
 *   - `0` as sentinel for null on FK fields
 *   - Y.Text for line_text instead of plain strings
 */

import * as Y from 'yjs';
import { uuidv4 } from 'lib0/random';

/**
 * Convert 0 → null for FK fields stored as 0 in the Y.Doc.
 * @param {*} val
 * @returns {*}
 */
export function zeroToNull(val) {
  return val === 0 ? null : val;
}

/**
 * Convert null → 0 for FK fields that need a non-null value in the Y.Doc.
 * @param {*} val
 * @returns {*}
 */
export function nullToZero(val) {
  return val == null ? 0 : val;
}

/**
 * Convert a Y.Map line from the Y.Doc to a plain object compatible with TMP_SCRIPT.
 *
 * @param {import('yjs').Map} lineYMap - A Y.Map representing a script line
 * @param {number|string} pageNo - The page number for this line
 * @returns {object} A plain line object for TMP_SCRIPT
 */
export function ydocLineToPlain(lineYMap, pageNo) {
  const lineId = zeroToNull(lineYMap.get('_id'));
  const partsArray = lineYMap.get('parts');
  const lineParts = [];

  if (partsArray) {
    for (let i = 0; i < partsArray.length; i++) {
      const partYMap = partsArray.get(i);
      const lineText = partYMap.get('line_text');
      lineParts.push({
        id: zeroToNull(partYMap.get('_id')),
        line_id: lineId,
        part_index: partYMap.get('part_index'),
        character_id: zeroToNull(partYMap.get('character_id')),
        character_group_id: zeroToNull(partYMap.get('character_group_id')),
        line_text: lineText ? lineText.toString() : '',
      });
    }
  }

  return {
    id: lineId,
    act_id: zeroToNull(lineYMap.get('act_id')),
    scene_id: zeroToNull(lineYMap.get('scene_id')),
    page: parseInt(pageNo, 10),
    line_type: lineYMap.get('line_type'),
    line_parts: lineParts,
    stage_direction_style_id: zeroToNull(lineYMap.get('stage_direction_style_id')),
  };
}

/**
 * Convert all lines on a Y.Doc page to an array of plain objects for TMP_SCRIPT.
 *
 * @param {import('yjs').Doc} ydoc - The Y.Doc instance
 * @param {number|string} pageNo - The page number to read
 * @returns {Array<object>} Array of plain line objects, or empty array if page doesn't exist
 */
export function syncPageFromYDoc(ydoc, pageNo) {
  const pages = ydoc.getMap('pages');
  const pageKey = pageNo.toString();
  const pageArray = pages.get(pageKey);
  if (!pageArray) return [];

  const lines = [];
  for (let i = 0; i < pageArray.length; i++) {
    lines.push(ydocLineToPlain(pageArray.get(i), pageNo));
  }
  return lines;
}

/**
 * Add a new line to a page in the Y.Doc.
 * Creates the necessary Y.Map, Y.Array, and Y.Text structures.
 *
 * @param {import('yjs').Doc} ydoc - The Y.Doc instance
 * @param {number|string} pageNo - The page number
 * @param {object} lineObj - The TMP_SCRIPT line object to add
 * @param {number} [insertAt] - Index to insert at. If omitted, appends to end.
 */
export function addYDocLine(ydoc, pageNo, lineObj, insertAt) {
  const pages = ydoc.getMap('pages');
  const pageKey = pageNo.toString();
  let pageArray = pages.get(pageKey);

  ydoc.transact(() => {
    // Create page array if it doesn't exist
    if (!pageArray) {
      pageArray = new Y.Array();
      pages.set(pageKey, pageArray);
    }

    const lineMap = new Y.Map();
    if (insertAt !== undefined && insertAt < pageArray.length) {
      pageArray.insert(insertAt, [lineMap]);
    } else {
      pageArray.push([lineMap]);
    }

    lineMap.set('_id', lineObj.id ? String(lineObj.id) : uuidv4());
    lineMap.set('act_id', nullToZero(lineObj.act_id));
    lineMap.set('scene_id', nullToZero(lineObj.scene_id));
    lineMap.set('line_type', lineObj.line_type);
    lineMap.set('stage_direction_style_id', nullToZero(lineObj.stage_direction_style_id));

    const partsArray = new Y.Array();
    lineMap.set('parts', partsArray);

    if (lineObj.line_parts) {
      lineObj.line_parts.forEach((part, i) => {
        const partMap = new Y.Map();
        partsArray.push([partMap]);

        partMap.set('_id', part.id ? String(part.id) : uuidv4());
        partMap.set('character_id', nullToZero(part.character_id));
        partMap.set('character_group_id', nullToZero(part.character_group_id));
        partMap.set('part_index', part.part_index ?? i);

        const ytext = new Y.Text();
        partMap.set('line_text', ytext);
        if (part.line_text) {
          ytext.insert(0, part.line_text);
        }
      });
    }
  }, 'local-bridge');
}

/**
 * Delete a line from a page in the Y.Doc.
 *
 * @param {import('yjs').Doc} ydoc - The Y.Doc instance
 * @param {number|string} pageNo - The page number
 * @param {number} lineIndex - Index of the line to delete
 */
export function deleteYDocLine(ydoc, pageNo, lineIndex) {
  const pages = ydoc.getMap('pages');
  const pageKey = pageNo.toString();
  const pageArray = pages.get(pageKey);
  if (!pageArray || lineIndex >= pageArray.length) return;

  ydoc.transact(() => {
    // If line has a real DB id (not a UUID), record it for backend deletion.
    // Use a strict all-digits test rather than parseInt — parseInt('3f1e…', 10)
    // returns 3, which would falsely classify UUIDs starting with a digit as DB ids.
    const lineMap = pageArray.get(lineIndex);
    if (lineMap) {
      const rawId = String(lineMap.get('_id') ?? '');
      if (/^\d+$/.test(rawId)) {
        const dbId = parseInt(rawId, 10);
        if (dbId > 0) {
          ydoc.getArray('deleted_line_ids').push([dbId]);
        }
      }
    }
    pageArray.delete(lineIndex, 1);
  }, 'local-bridge');
}
