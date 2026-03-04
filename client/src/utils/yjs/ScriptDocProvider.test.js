import { describe, it, expect, beforeEach, vi } from 'vitest';
import * as Y from 'yjs';
import ScriptDocProvider, { encodeBase64, decodeBase64 } from './ScriptDocProvider';

// ScriptDocProvider uses Vue.prototype.$socket — stub it so the module loads
vi.mock('vue', () => ({
  default: { prototype: {} },
}));

function makeDoc() {
  return new Y.Doc();
}

function makeProvider() {
  const doc = makeDoc();
  const provider = new ScriptDocProvider(doc);
  return { provider, doc };
}

function encodedUpdate(doc) {
  return encodeBase64(Y.encodeStateAsUpdate(doc));
}

function encodedStateVector(doc) {
  return encodeBase64(Y.encodeStateVector(doc));
}

function encodedAwareness(state) {
  return encodeBase64(new TextEncoder().encode(JSON.stringify(state)));
}

describe('ScriptDocProvider', () => {
  describe('applySync()', () => {
    it('returns false when payload is missing', () => {
      const { provider } = makeProvider();
      const result = provider.applySync({ step: 0 });
      expect(result).toBe(false);
    });

    it('step 0: applies full state, sets _synced, returns true', () => {
      const { provider, doc } = makeProvider();
      const sourceDoc = makeDoc();
      const meta = sourceDoc.getMap('meta');
      meta.set('revision_id', 42);

      const result = provider.applySync({
        step: 0,
        payload: encodedUpdate(sourceDoc),
      });

      expect(result).toBe(true);
      expect(provider.synced).toBe(true);
      expect(doc.getMap('meta').get('revision_id')).toBe(42);
    });

    it('step 0: accepts message without room_id (no filtering)', () => {
      const { provider } = makeProvider();
      const sourceDoc = makeDoc();
      const result = provider.applySync({
        step: 0,
        payload: encodedUpdate(sourceDoc),
      });
      expect(result).toBe(true);
    });

    it('step 0: accepts message with room_id (ignored, not filtered)', () => {
      const { provider } = makeProvider();
      const sourceDoc = makeDoc();
      // room_id is present but should be ignored — server no longer sends it,
      // but provider must still handle it gracefully for backwards compatibility
      const result = provider.applySync({
        room_id: 'draft_99',
        step: 0,
        payload: encodedUpdate(sourceDoc),
      });
      expect(result).toBe(true);
    });

    it('step 2: applies diff, returns true', () => {
      const { provider, doc } = makeProvider();

      // First sync step 0 to get a baseline
      const sourceDoc = makeDoc();
      provider.applySync({ step: 0, payload: encodedUpdate(sourceDoc) });

      // Now produce a diff and apply as step 2
      const sv = Y.encodeStateVector(doc);
      sourceDoc.getMap('meta').set('new_key', 'new_val');
      const diff = Y.encodeStateAsUpdate(sourceDoc, sv);

      const result = provider.applySync({
        step: 2,
        payload: encodeBase64(diff),
      });

      expect(result).toBe(true);
      expect(doc.getMap('meta').get('new_key')).toBe('new_val');
    });
  });

  describe('applyUpdate()', () => {
    it('returns false when not connected', () => {
      const { provider } = makeProvider();
      provider._connected = false;
      expect(provider.applyUpdate({ payload: 'dA==' })).toBe(false);
    });

    it('returns false when payload is missing', () => {
      const { provider } = makeProvider();
      provider._connected = true;
      expect(provider.applyUpdate({})).toBe(false);
    });

    it('applies update to doc and returns true', () => {
      const { provider, doc } = makeProvider();
      provider._connected = true;

      const sourceDoc = makeDoc();
      const sv = Y.encodeStateVector(doc);
      sourceDoc.getMap('data').set('key', 'value');
      const update = Y.encodeStateAsUpdate(sourceDoc, sv);

      const result = provider.applyUpdate({ payload: encodeBase64(update) });

      expect(result).toBe(true);
      expect(doc.getMap('data').get('key')).toBe('value');
    });

    it('applies update even when room_id is present (ignored)', () => {
      const { provider, doc } = makeProvider();
      provider._connected = true;

      const sourceDoc = makeDoc();
      const sv = Y.encodeStateVector(doc);
      sourceDoc.getMap('data').set('key', 'value');
      const update = Y.encodeStateAsUpdate(sourceDoc, sv);

      // room_id no longer causes filtering
      const result = provider.applyUpdate({
        room_id: 'draft_99',
        payload: encodeBase64(update),
      });

      expect(result).toBe(true);
    });
  });

  describe('applyAwareness()', () => {
    it('returns false when not connected', () => {
      const { provider } = makeProvider();
      provider._connected = false;
      expect(provider.applyAwareness({ payload: 'dA==' })).toBe(false);
    });

    it('returns true when payload is missing', () => {
      const { provider } = makeProvider();
      provider._connected = true;
      expect(provider.applyAwareness({})).toBe(true);
    });

    it('decodes payload and returns AWARENESS result', () => {
      const { provider } = makeProvider();
      provider._connected = true;

      const state = { userId: 7, username: 'alice', page: 2, lineIndex: 5 };
      const result = provider.applyAwareness({ payload: encodedAwareness(state) });

      expect(result).toEqual({ type: 'AWARENESS', state });
    });

    it('handles message without room_id', () => {
      const { provider } = makeProvider();
      provider._connected = true;

      const state = { userId: 3, page: null, lineIndex: null };
      const result = provider.applyAwareness({ payload: encodedAwareness(state) });

      expect(result).toEqual({ type: 'AWARENESS', state });
    });

    it('applies awareness even when room_id is present (ignored)', () => {
      const { provider } = makeProvider();
      provider._connected = true;

      const state = { userId: 5, page: 1, lineIndex: 2 };
      // room_id no longer causes filtering
      const result = provider.applyAwareness({
        room_id: 'draft_99',
        payload: encodedAwareness(state),
      });

      expect(result).toEqual({ type: 'AWARENESS', state });
    });
  });
});
