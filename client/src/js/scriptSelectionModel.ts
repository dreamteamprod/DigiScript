/**
 * The core logic behind Design E's contiguous-range line selection, shared by
 * ScriptEditor.vue and CollabScriptEditor.vue (index-based in both — the
 * collab side maps indices to line uids for its own storage, but the range
 * transitions themselves are identical) and by both editors' own hover-preview
 * computation, so there is exactly one place that decides what a tick does.
 */

export interface SelectionRange {
  startIndex: number;
  endIndex: number;
}

/**
 * Given the current selection range (or null if nothing is selected) and the
 * index of the line just ticked, returns the new range — or null if the
 * selection should clear entirely.
 *
 * - No active selection: the ticked line becomes a fresh single-line range.
 * - Ticking before the range's start, or after its end: extends that side.
 * - Ticking the sole selected line again: clears the selection.
 * - Ticking the range's own start or end line (when there's more than one
 *   line selected): shrinks the range by one from that end, keeping it
 *   contiguous — deselects just that one line, leaves the rest selected.
 * - Ticking a genuinely interior line (neither boundary): collapses the
 *   range down to just that line. Removing an interior line can't keep the
 *   rest of the range in one contiguous block either way, so this doubles as
 *   a "restart the selection here" gesture.
 */
export function nextSelectionRange(
  current: SelectionRange | null,
  clickedIndex: number
): SelectionRange | null {
  if (!current) {
    return { startIndex: clickedIndex, endIndex: clickedIndex };
  }
  const { startIndex, endIndex } = current;
  if (clickedIndex < startIndex) {
    return { startIndex: clickedIndex, endIndex };
  }
  if (clickedIndex > endIndex) {
    return { startIndex, endIndex: clickedIndex };
  }
  if (startIndex === endIndex && clickedIndex === startIndex) {
    return null;
  }
  if (clickedIndex === startIndex) {
    return { startIndex: clickedIndex + 1, endIndex };
  }
  if (clickedIndex === endIndex) {
    return { startIndex, endIndex: clickedIndex - 1 };
  }
  return { startIndex: clickedIndex, endIndex: clickedIndex };
}
