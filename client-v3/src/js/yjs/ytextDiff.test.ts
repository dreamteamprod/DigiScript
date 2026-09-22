import { describe, it, expect } from 'vitest';
import * as Y from 'yjs';
import { computeTextDiff, applyTextDiff, captureSelection, resolveSelection } from './ytextDiff';

function apply(oldText: string, diff: { index: number; deleteCount: number; insert: string }) {
  return oldText.slice(0, diff.index) + diff.insert + oldText.slice(diff.index + diff.deleteCount);
}

function syncedDocs(initial: string): { a: Y.Doc; b: Y.Doc; textA: Y.Text; textB: Y.Text } {
  const a = new Y.Doc();
  a.getText('t').insert(0, initial);
  const b = new Y.Doc();
  Y.applyUpdate(b, Y.encodeStateAsUpdate(a));
  return { a, b, textA: a.getText('t'), textB: b.getText('t') };
}

function sync(a: Y.Doc, b: Y.Doc): void {
  Y.applyUpdate(b, Y.encodeStateAsUpdate(a, Y.encodeStateVector(b)));
  Y.applyUpdate(a, Y.encodeStateAsUpdate(b, Y.encodeStateVector(a)));
}

describe('computeTextDiff', () => {
  it.each([
    ['hello', 'hello', null],
    ['hello', 'hello!', { index: 5, deleteCount: 0, insert: '!' }],
    ['hello', 'ello', { index: 0, deleteCount: 1, insert: '' }],
    ['hello', 'hexllo', { index: 2, deleteCount: 0, insert: 'x' }],
    ['hello world', 'hello brave world', { index: 6, deleteCount: 0, insert: 'brave ' }],
    ['abc', 'axc', { index: 1, deleteCount: 1, insert: 'x' }],
    ['', 'hi', { index: 0, deleteCount: 0, insert: 'hi' }],
    ['hi', '', { index: 0, deleteCount: 2, insert: '' }],
  ])('%j → %j', (oldText, newText, expected) => {
    expect(computeTextDiff(oldText, newText)).toEqual(expected);
  });

  it('does not let the suffix overlap the prefix (aaa → aa is one deletion)', () => {
    const diff = computeTextDiff('aaa', 'aa');
    expect(diff).toEqual({ index: 2, deleteCount: 1, insert: '' });
  });

  it('touches only the changed characters, never the whole string', () => {
    const diff = computeTextDiff('the quick brown fox', 'the quick red fox');
    expect(diff!.deleteCount).toBeLessThan('the quick brown fox'.length);
    expect(diff!.insert.length).toBeLessThan('the quick red fox'.length);
  });

  it('keeps a surrogate pair together when the change is next to an emoji', () => {
    // 😀 is U+1F600 = D83D DE00. Replacing it with 😁 (D83D DE01) shares the high half.
    const oldText = 'a😀b';
    const newText = 'a😁b';
    const diff = computeTextDiff(oldText, newText)!;

    expect(diff).toEqual({ index: 1, deleteCount: 2, insert: '😁' });
    expect(apply(oldText, diff)).toBe(newText);
  });

  it('never splits a pair when only the low surrogates match (suffix rule)', () => {
    // 😀 = D83D DE00 and 🨀 = D83E DE00 share the *low* half, so the common suffix
    // would start in the middle of the pair unless it is backed off.
    const oldText = 'a😀';
    const newText = 'a🨀';
    const diff = computeTextDiff(oldText, newText)!;

    expect(diff).toEqual({ index: 1, deleteCount: 2, insert: '🨀' });
    expect(apply(oldText, diff)).toBe(newText);
  });

  it('keeps the pair together on the suffix side too', () => {
    const oldText = '😀!';
    const newText = '😁!';
    expect(apply(oldText, computeTextDiff(oldText, newText)!)).toBe(newText);
    expect(computeTextDiff(oldText, newText)!.index).toBe(0);
  });

  it('round-trips random edits, never splitting a surrogate pair', () => {
    // Deterministic PRNG so a failure reproduces.
    let seed = 1234567;
    const rand = () => {
      seed = (seed * 1103515245 + 12345) & 0x7fffffff;
      return seed / 0x7fffffff;
    };
    const alphabet = ['a', 'b', ' ', '😀', '😁', '🨀', 'é'];
    const randomString = () =>
      Array.from(
        { length: Math.floor(rand() * 8) },
        () => alphabet[Math.floor(rand() * alphabet.length)]
      ).join('');

    for (let i = 0; i < 2000; i += 1) {
      const oldText = randomString();
      const newText = randomString();
      const diff = computeTextDiff(oldText, newText);
      if (diff === null) {
        expect(oldText).toBe(newText);
        continue;
      }
      expect(apply(oldText, diff)).toBe(newText);
      const before = oldText.charCodeAt(diff.index - 1);
      const startsInsideAPair =
        diff.index > 0 && before >= 0xd800 && before <= 0xdbff && oldText.length > diff.index;
      expect(startsInsideAPair).toBe(false);
      // ...nor ends inside one (the suffix rule).
      const end = diff.index + diff.deleteCount;
      const endsInsideAPair =
        end > 0 &&
        end < oldText.length &&
        oldText.charCodeAt(end - 1) >= 0xd800 &&
        oldText.charCodeAt(end - 1) <= 0xdbff;
      expect(endsInsideAPair).toBe(false);
    }
  });
});

describe('applyTextDiff', () => {
  it('writes only the changed characters (no delete-everything/insert-everything)', () => {
    const { textA } = syncedDocs('hello world');
    const deltas: unknown[] = [];
    textA.observe((event) => deltas.push(event.delta));

    applyTextDiff(textA, 'hello brave world', 'local-edit');

    expect(deltas).toEqual([[{ retain: 6 }, { insert: 'brave ' }]]);
  });

  it('is a no-op when nothing changed', () => {
    const { textA, a } = syncedDocs('same');
    let updates = 0;
    a.on('update', () => {
      updates += 1;
    });

    expect(applyTextDiff(textA, 'same', 'local-edit')).toBe(false);
    expect(updates).toBe(0);
  });

  it('is one transaction with the given origin, even when it deletes and inserts', () => {
    const { textA, a } = syncedDocs('abc');
    const origins: unknown[] = [];
    a.on('update', (_update: Uint8Array, origin: unknown) => origins.push(origin));

    applyTextDiff(textA, 'axc', 'local-edit');

    expect(origins).toEqual(['local-edit']);
    expect(textA.toString()).toBe('axc');
  });

  it("keeps both people's edits when two people type in the same field", () => {
    const { a, b, textA, textB } = syncedDocs('hello world');

    applyTextDiff(textA, 'Oh, hello world', 'local-edit'); // A prepends
    applyTextDiff(textB, 'hello world!', 'local-edit'); // B appends
    sync(a, b);

    expect(textA.toString()).toBe('Oh, hello world!');
    expect(textB.toString()).toBe('Oh, hello world!');
  });

  it('converges when both edit the middle of the same word', () => {
    const { a, b, textA, textB } = syncedDocs('color');

    applyTextDiff(textA, 'colour', 'local-edit');
    applyTextDiff(textB, 'colors', 'local-edit');
    sync(a, b);

    expect(textA.toString()).toBe(textB.toString());
    expect(textA.toString()).toContain('u');
    expect(textA.toString()).toContain('s');
  });

  it("why it matters: replacing the whole field on every edit loses the other person's edit", () => {
    const { a, b, textA, textB } = syncedDocs('hello world');
    const replaceAll = (text: Y.Text, value: string) => {
      text.delete(0, text.length);
      text.insert(0, value);
    };

    replaceAll(textA, 'Oh, hello world');
    replaceAll(textB, 'hello world!');
    sync(a, b);

    // The two "whole field" replacements can't both survive — this is the bug the
    // minimal diff exists to prevent.
    expect(textA.toString()).not.toBe('Oh, hello world!');
  });
});

describe('captureSelection / resolveSelection', () => {
  it('keeps the caret on the same text when another editor types before it', () => {
    const { a, b, textA, textB } = syncedDocs('hello world');
    const selection = captureSelection(textA, 5, 5); // after "hello"

    applyTextDiff(textB, 'Oh, hello world', 'local-edit');
    sync(a, b);

    expect(resolveSelection(textA, selection)).toEqual({ start: 9, end: 9 });
  });

  it('does not move the caret when another editor types after it', () => {
    const { a, b, textA, textB } = syncedDocs('hello world');
    const selection = captureSelection(textA, 5, 5);

    applyTextDiff(textB, 'hello world!!', 'local-edit');
    sync(a, b);

    expect(resolveSelection(textA, selection)).toEqual({ start: 5, end: 5 });
  });

  it('leaves the caret behind text another editor inserts exactly at it', () => {
    const { a, b, textA, textB } = syncedDocs('hello world');
    const selection = captureSelection(textA, 5, 5);

    applyTextDiff(textB, 'hello,, world', 'local-edit'); // inserted at index 5
    sync(a, b);

    expect(resolveSelection(textA, selection)).toEqual({ start: 5, end: 5 });
  });

  it('follows a selection through edits on both sides of it', () => {
    const { a, b, textA, textB } = syncedDocs('hello world');
    const selection = captureSelection(textA, 6, 11); // "world"

    // Two separate edits, as two separate keystrokes/pastes would be. (One call that
    // changed both ends would be a single replace-everything diff, which by definition
    // deletes the selected text.)
    applyTextDiff(textB, '>> hello world', 'local-edit');
    applyTextDiff(textB, '>> hello world <<', 'local-edit');
    sync(a, b);

    const resolved = resolveSelection(textA, selection)!;
    expect(textA.toString().slice(resolved.start, resolved.end)).toBe('world');
  });

  it('collapses a caret whose text was deleted', () => {
    const { a, b, textA, textB } = syncedDocs('hello big world');
    const selection = captureSelection(textA, 8, 8); // inside "big"

    applyTextDiff(textB, 'hello world', 'local-edit'); // "big " removed
    sync(a, b);

    const resolved = resolveSelection(textA, selection)!;
    expect(resolved.start).toBe(resolved.end);
    expect(resolved.start).toBeLessThanOrEqual('hello world'.length);
  });

  it('returns null for text that is not part of a doc', () => {
    const { textA } = syncedDocs('x');
    const selection = captureSelection(textA, 0, 0);

    expect(resolveSelection(new Y.Text('detached'), selection)).toBeNull();
  });

  it('returns null for a selection captured on a different text in the same doc', () => {
    const doc = new Y.Doc();
    const first = doc.getText('first');
    const second = doc.getText('second');
    first.insert(0, 'hello world');
    second.insert(0, 'hello world');
    const selection = captureSelection(first, 6, 11);

    expect(resolveSelection(second, selection)).toBeNull();
    expect(resolveSelection(first, selection)).toEqual({ start: 6, end: 11 });
  });
});
