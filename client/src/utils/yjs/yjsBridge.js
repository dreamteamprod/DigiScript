/**
 * Bridge utilities for converting between Y.Doc and TMP_SCRIPT formats.
 *
 * The Y.Doc uses a slightly different schema than TMP_SCRIPT:
 *   - `_id` instead of `id`
 *   - `parts` instead of `line_parts`
 *   - `0` as sentinel for null on FK fields
 *   - Y.Text for line_text instead of plain strings
 *
 * These utilities handle the conversion in both directions.
 */

import * as Y from 'yjs';

/**
 * Convert 0 → null for FK fields stored as 0 in the Y.Doc.
 * @param {*} val
 * @returns {*}
 */
function zeroToNull(val) {
  return val === 0 ? null : val;
}

/**
 * Convert null → 0 for FK fields that need a non-null value in the Y.Doc.
 * @param {*} val
 * @returns {*}
 */
function nullToZero(val) {
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
 * Update a single existing line in the Y.Doc from a TMP_SCRIPT line object.
 * Uses 'local-bridge' as the transaction origin so observers can
 * distinguish local UI changes from remote changes.
 *
 * @param {import('yjs').Doc} ydoc - The Y.Doc instance
 * @param {number|string} pageNo - The page number
 * @param {number} lineIndex - Index of the line within the page array
 * @param {object} lineObj - The TMP_SCRIPT line object
 */
export function updateYDocLine(ydoc, pageNo, lineIndex, lineObj) {
  const pages = ydoc.getMap('pages');
  const pageKey = pageNo.toString();
  const pageArray = pages.get(pageKey);
  if (!pageArray || lineIndex >= pageArray.length) return;

  const lineMap = pageArray.get(lineIndex);

  ydoc.transact(() => {
    lineMap.set('act_id', nullToZero(lineObj.act_id));
    lineMap.set('scene_id', nullToZero(lineObj.scene_id));
    lineMap.set('line_type', lineObj.line_type);
    lineMap.set('stage_direction_style_id', nullToZero(lineObj.stage_direction_style_id));

    const partsArray = lineMap.get('parts');
    if (!partsArray) return;

    // Update existing parts
    const minLen = Math.min(partsArray.length, lineObj.line_parts.length);
    for (let i = 0; i < minLen; i++) {
      const part = lineObj.line_parts[i];
      const partMap = partsArray.get(i);

      partMap.set('character_id', nullToZero(part.character_id));
      partMap.set('character_group_id', nullToZero(part.character_group_id));
      partMap.set('part_index', part.part_index ?? i);

      const ytext = partMap.get('line_text');
      if (ytext) {
        const currentText = ytext.toString();
        if (currentText !== (part.line_text || '')) {
          ytext.delete(0, ytext.length);
          if (part.line_text) {
            ytext.insert(0, part.line_text);
          }
        }
      }
    }

    // Add new parts that don't exist in Y.Doc yet
    for (let i = partsArray.length; i < lineObj.line_parts.length; i++) {
      const part = lineObj.line_parts[i];
      const newPartMap = new Y.Map();
      partsArray.push([newPartMap]);

      newPartMap.set('_id', 0);
      newPartMap.set('character_id', nullToZero(part.character_id));
      newPartMap.set('character_group_id', nullToZero(part.character_group_id));
      newPartMap.set('part_index', part.part_index ?? i);

      const ytext = new Y.Text();
      newPartMap.set('line_text', ytext);
      if (part.line_text) {
        ytext.insert(0, part.line_text);
      }
    }

    // Remove extra parts from Y.Doc (if user deleted parts)
    while (partsArray.length > lineObj.line_parts.length) {
      partsArray.delete(partsArray.length - 1, 1);
    }
  }, 'local-bridge');
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

    lineMap.set('_id', nullToZero(lineObj.id));
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

        partMap.set('_id', nullToZero(part.id));
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
    pageArray.delete(lineIndex, 1);
  }, 'local-bridge');
}
