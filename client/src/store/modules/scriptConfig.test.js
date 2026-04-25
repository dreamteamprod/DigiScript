import { vi } from 'vitest';

// Stub external dependencies before importing scriptConfig
vi.mock('vue', () => ({
  default: { prototype: {}, set: vi.fn(), delete: vi.fn() },
  set: vi.fn(),
  delete: vi.fn(),
}));
vi.mock('loglevel', () => ({
  default: { debug: vi.fn(), info: vi.fn(), error: vi.fn(), warn: vi.fn() },
}));
vi.mock('deep-object-diff', () => ({
  detailedDiff: vi.fn(() => ({ added: {}, updated: {}, deleted: {} })),
}));
vi.mock('@/js/utils', () => ({
  makeURL: vi.fn((path) => `http://localhost${path}`),
}));

import scriptConfigModule from './scriptConfig';

const { getters } = scriptConfigModule;

function makeState(overrides = {}) {
  return {
    editStatus: { editors: [], cutters: [], hasDraft: false },
    ...overrides,
  };
}

describe('scriptConfig getters', () => {
  describe('CAN_REQUEST_EDIT', () => {
    it('returns false when a live session is active (no cutters)', () => {
      const state = makeState();
      const result = getters.CAN_REQUEST_EDIT(state, {}, {}, { CURRENT_SHOW_SESSION: { id: 1 } });
      expect(result).toBe(false);
    });

    it('returns false when live session is active even if cutters also present', () => {
      const state = makeState({
        editStatus: { editors: [], cutters: [{ internal_id: 'x' }], hasDraft: false },
      });
      const result = getters.CAN_REQUEST_EDIT(state, {}, {}, { CURRENT_SHOW_SESSION: { id: 1 } });
      expect(result).toBe(false);
    });

    it('returns true when no live session and no cutters', () => {
      const state = makeState();
      const result = getters.CAN_REQUEST_EDIT(state, {}, {}, { CURRENT_SHOW_SESSION: null });
      expect(result).toBe(true);
    });

    it('returns false when no live session but cutters exist', () => {
      const state = makeState({
        editStatus: { editors: [], cutters: [{ internal_id: 'x' }], hasDraft: false },
      });
      const result = getters.CAN_REQUEST_EDIT(state, {}, {}, { CURRENT_SHOW_SESSION: null });
      expect(result).toBe(false);
    });
  });

  describe('CAN_REQUEST_CUTS', () => {
    it('returns false when a live session is active (all else clear)', () => {
      const state = makeState();
      const result = getters.CAN_REQUEST_CUTS(state, {}, {}, { CURRENT_SHOW_SESSION: { id: 1 } });
      expect(result).toBe(false);
    });

    it('returns true when no live session and all else clear', () => {
      const state = makeState();
      const result = getters.CAN_REQUEST_CUTS(state, {}, {}, { CURRENT_SHOW_SESSION: null });
      expect(result).toBe(true);
    });

    it('returns false when no live session but an editor exists', () => {
      const state = makeState({
        editStatus: { editors: [{ internal_id: 'y' }], cutters: [], hasDraft: false },
      });
      const result = getters.CAN_REQUEST_CUTS(state, {}, {}, { CURRENT_SHOW_SESSION: null });
      expect(result).toBe(false);
    });

    it('returns false when no live session but a cutter exists', () => {
      const state = makeState({
        editStatus: { editors: [], cutters: [{ internal_id: 'z' }], hasDraft: false },
      });
      const result = getters.CAN_REQUEST_CUTS(state, {}, {}, { CURRENT_SHOW_SESSION: null });
      expect(result).toBe(false);
    });

    it('returns false when no live session but a draft exists', () => {
      const state = makeState({
        editStatus: { editors: [], cutters: [], hasDraft: true },
      });
      const result = getters.CAN_REQUEST_CUTS(state, {}, {}, { CURRENT_SHOW_SESSION: null });
      expect(result).toBe(false);
    });
  });
});
