import * as Y from 'yjs';

/**
 * The smallest single edit (one deletion plus one insertion at the same index) that
 * turns one string into another, widened where needed so it never starts or ends inside
 * a surrogate pair (so it can be a character or two longer than strictly minimal).
 *
 * Writing a text field to a `Y.Text` must use this rather than "delete everything,
 * insert the new value": the latter makes every keystroke a fresh replacement of the
 * whole field, so two people typing in the same field overwrite each other instead of
 * merging. Only the characters that actually changed are touched.
 */
export interface TextDiff {
  index: number;
  deleteCount: number;
  insert: string;
}

const isHighSurrogate = (code: number): boolean => code >= 0xd800 && code <= 0xdbff;
const isLowSurrogate = (code: number): boolean => code >= 0xdc00 && code <= 0xdfff;

/** Returns null when the strings are equal (nothing to write). */
export function computeTextDiff(oldText: string, newText: string): TextDiff | null {
  if (oldText === newText) return null;

  const shorter = Math.min(oldText.length, newText.length);
  let prefix = 0;
  while (prefix < shorter && oldText.charCodeAt(prefix) === newText.charCodeAt(prefix)) {
    prefix += 1;
  }
  // The suffix may not overlap the prefix ("aaa" → "aa" is one deletion, not two).
  let suffix = 0;
  while (
    suffix < shorter - prefix &&
    oldText.charCodeAt(oldText.length - 1 - suffix) ===
      newText.charCodeAt(newText.length - 1 - suffix)
  ) {
    suffix += 1;
  }

  // Yjs indexes UTF-16 code units. An edit that lands between the two halves of a
  // surrogate pair (an emoji) would leave a lone surrogate in the shared text, which
  // a concurrent edit can then separate for good — keep the pair on one side.
  if (prefix > 0 && isHighSurrogate(oldText.charCodeAt(prefix - 1))) {
    prefix -= 1;
  }
  if (suffix > 0 && isLowSurrogate(oldText.charCodeAt(oldText.length - suffix))) {
    suffix -= 1;
  }

  return {
    index: prefix,
    deleteCount: oldText.length - prefix - suffix,
    insert: newText.slice(prefix, newText.length - suffix),
  };
}

/**
 * Make `ytext` equal `newText` with the minimal edit, as one transaction tagged with
 * `origin`. Returns whether anything was written.
 */
export function applyTextDiff(ytext: Y.Text, newText: string, origin: unknown): boolean {
  const diff = computeTextDiff(ytext.toString(), newText);
  if (diff === null) return false;

  const write = (): void => {
    if (diff.deleteCount > 0) ytext.delete(diff.index, diff.deleteCount);
    if (diff.insert.length > 0) ytext.insert(diff.index, diff.insert);
  };
  if (ytext.doc) {
    ytext.doc.transact(write, origin);
  } else {
    write();
  }
  return true;
}

/** A caret/selection that follows the text it was on as other people edit around it. */
export interface RelativeSelection {
  start: Y.RelativePosition;
  end: Y.RelativePosition;
}

// assoc -1 attaches a position to the character on its left, so text another editor
// inserts exactly at the caret lands after it and the caret doesn't jump.
const ASSOC_LEFT = -1;

/** Capture a selection (plain string indexes) so it survives remote edits. */
export function captureSelection(ytext: Y.Text, start: number, end: number): RelativeSelection {
  return {
    start: Y.createRelativePositionFromTypeIndex(ytext, start, ASSOC_LEFT),
    end: Y.createRelativePositionFromTypeIndex(ytext, end, ASSOC_LEFT),
  };
}

/**
 * Where a captured selection is now, or null if the text is no longer part of a doc,
 * the position can't be resolved, or it was captured on a different text.
 */
export function resolveSelection(
  ytext: Y.Text,
  selection: RelativeSelection
): { start: number; end: number } | null {
  const doc = ytext.doc;
  if (!doc) return null;
  const start = Y.createAbsolutePositionFromRelativePosition(selection.start, doc);
  const end = Y.createAbsolutePositionFromRelativePosition(selection.end, doc);
  if (!start || !end) return null;
  // A position resolves against the whole doc, so one captured on another text (say a
  // different part's) would otherwise return an unrelated index without complaint.
  if (start.type !== ytext || end.type !== ytext) return null;
  return { start: start.index, end: end.index };
}
