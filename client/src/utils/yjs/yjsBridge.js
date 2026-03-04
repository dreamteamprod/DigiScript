/**
 * Bridge utilities for Y.Doc structural operations.
 *
 * Y.Doc is the source of truth during collaborative editing.
 * Components write directly to Y.Map/Y.Text; this module provides:
 *   - Structural helpers (add/delete lines in Y.Doc)
 *   - Sentinel conversion (nullToZero / zeroToNull)
 *
 * Y.Doc schema:
 *   - `_id` for line/part IDs (string; numeric DB id or UUID for new items)
 *   - `parts` (Y.Array of Y.Map) instead of `line_parts`
 *   - `0` as sentinel for null on FK fields
 *   - Y.Text for line_text instead of plain strings
 */

import * as Y from 'yjs';
import { uuidv4 } from 'lib0/random';

export function zeroToNull(val) {
  return val === 0 ? null : val;
}

export function nullToZero(val) {
  return val == null ? 0 : val;
}

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
