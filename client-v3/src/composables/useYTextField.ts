import { ref, nextTick, onUnmounted, type Ref } from 'vue';
import * as Y from 'yjs';
import { captureSelection, resolveSelection, type RelativeSelection } from '@/js/yjs/ytextDiff';
import { LOCAL_EDIT_ORIGIN } from '@/js/yjs/draftWriter';

export interface YTextFieldBinding {
  /** The field's current text, kept in sync with the `Y.Text` (local and remote edits alike). */
  value: Ref<string>;
  /** Bind this to the input element (`ref="inputRef"`). */
  inputRef: Ref<HTMLInputElement | null>;
  /** Call on `@update:model-value` (or `@input`) with the new text. */
  onInput: (newValue: string) => void;
  /** Call on any event that can move the caret without going through `onInput` (click, keyup, focus, select). */
  onCaretActivity: () => void;
}

/**
 * Binds a text input to a live `Y.Text`, so the field shows a remote editor's typing as
 * it happens and a caret sitting in the field follows the character it was on rather
 * than a raw index — a remote insert earlier in the text must not make the local caret
 * appear to jump.
 *
 * `getText`/`writeText` are passed in rather than a `Y.Text` directly: the target can be
 * removed and recreated (e.g. the containing part is removed and a new one added) across
 * the field's lifetime, and nothing here may hold a `Y.Text` across such a change.
 */
export function useYTextField(
  getText: () => Y.Text | null,
  writeText: (text: string) => void
): YTextFieldBinding {
  const value = ref('');
  const inputRef = ref<HTMLInputElement | null>(null);
  let observedText: Y.Text | null = null;
  let lastSelection: RelativeSelection | null = null;

  function captureCaret(): void {
    const yt = getText();
    const el = inputRef.value;
    if (!yt || !el) return;
    lastSelection = captureSelection(yt, el.selectionStart ?? 0, el.selectionEnd ?? 0);
  }

  function restoreCaret(): void {
    const yt = getText();
    const el = inputRef.value;
    if (!yt || !el || !lastSelection) return;
    const resolved = resolveSelection(yt, lastSelection);
    if (!resolved) return;
    el.setSelectionRange(resolved.start, resolved.end);
  }

  function onTextChange(_event: Y.YTextEvent, transaction: Y.Transaction): void {
    const yt = observedText;
    if (!yt) return;
    value.value = yt.toString();
    // A local write already leaves the DOM caret exactly where the user left it (the
    // input's own value already matches, so Vue won't touch it); only a remote change
    // needs the caret actively restored.
    if (transaction.origin === LOCAL_EDIT_ORIGIN) return;
    if (document.activeElement === inputRef.value) {
      void nextTick(restoreCaret);
    }
  }

  function observe(): void {
    const yt = getText();
    if (yt === observedText) return;
    if (observedText) observedText.unobserve(onTextChange);
    observedText = yt;
    if (yt) yt.observe(onTextChange);
    value.value = yt ? yt.toString() : '';
  }

  function onInput(newValue: string): void {
    observe();
    writeText(newValue);
    // Re-anchor to where the user's own typing left the caret, so a remote edit that
    // lands before the next keystroke restores it correctly.
    captureCaret();
  }

  function onCaretActivity(): void {
    captureCaret();
  }

  observe();
  onUnmounted(() => {
    if (observedText) observedText.unobserve(onTextChange);
  });

  return { value, inputRef, onInput, onCaretActivity };
}
