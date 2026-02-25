import { describe, it, expect, vi, beforeEach } from 'vitest';

// Stub external dependencies before importing scriptDraft
vi.mock('vue', () => ({
  default: { prototype: {}, set: vi.fn(), delete: vi.fn() },
  set: vi.fn(),
  delete: vi.fn(),
}));
vi.mock('loglevel', () => ({
  default: { debug: vi.fn(), info: vi.fn(), error: vi.fn(), warn: vi.fn() },
}));
vi.mock('yjs', () => ({
  Doc: vi.fn(() => ({
    on: vi.fn(),
    off: vi.fn(),
    getMap: vi.fn(() => ({ set: vi.fn() })),
    getArray: vi.fn(() => []),
  })),
}));
vi.mock('@/utils/yjs/ScriptDocProvider', () => ({
  default: vi.fn(),
}));

import log from 'loglevel';
import scriptDraftModule from './scriptDraft';

const { actions } = scriptDraftModule;

/**
 * Create a minimal mock Vuex action context.
 */
function makeContext(stateOverrides = {}) {
  const commits = [];
  const dispatches = [];
  return {
    state: { isSynced: false, roomId: null, ...stateOverrides },
    commit: vi.fn((type, payload) => commits.push({ type, payload })),
    dispatch: vi.fn((type, payload) => dispatches.push({ type, payload })),
    _commits: commits,
    _dispatches: dispatches,
  };
}

describe('scriptDraft Vuex actions', () => {
  describe('ROOM_MEMBERS', () => {
    it('commits SET_DRAFT_COLLABORATORS with members from DATA', () => {
      const context = makeContext();
      const members = [{ user_id: 1, username: 'alice', role: 'editor' }];
      actions.ROOM_MEMBERS(context, { DATA: { members } });
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_COLLABORATORS', members);
    });

    it('commits empty array when DATA.members is missing', () => {
      const context = makeContext();
      actions.ROOM_MEMBERS(context, { DATA: {} });
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_COLLABORATORS', []);
    });

    it('commits empty array when DATA is missing', () => {
      const context = makeContext();
      actions.ROOM_MEMBERS(context, {});
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_COLLABORATORS', []);
    });
  });

  describe('ROOM_CLOSED', () => {
    it('dispatches LEAVE_DRAFT_ROOM', () => {
      const context = makeContext();
      actions.ROOM_CLOSED(context);
      expect(context.dispatch).toHaveBeenCalledWith('LEAVE_DRAFT_ROOM');
    });
  });

  describe('SCRIPT_SAVED', () => {
    it('clears saving state and commits timestamp', () => {
      const context = makeContext();
      const now = '2026-02-25T12:00:00Z';
      actions.SCRIPT_SAVED(context, { DATA: { last_saved_at: now } });
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_SAVING', false);
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_SAVE_PHASE', null);
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_SAVE_ERROR', null);
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_LAST_SAVED', now);
    });

    it('does not commit timestamp when last_saved_at is absent', () => {
      const context = makeContext();
      actions.SCRIPT_SAVED(context, { DATA: {} });
      expect(context.commit).not.toHaveBeenCalledWith('SET_DRAFT_LAST_SAVED', expect.anything());
    });
  });

  describe('SAVE_PROGRESS', () => {
    it('sets saving true and commits progress data', () => {
      const context = makeContext();
      const data = { page: 1, total: 5, percent: 20 };
      actions.SAVE_PROGRESS(context, { DATA: data });
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_SAVING', true);
      expect(context.commit).toHaveBeenCalledWith('SET_SAVE_PROGRESS', data);
    });
  });

  describe('SAVE_ERROR', () => {
    it('clears saving state and commits error message', () => {
      const context = makeContext();
      actions.SAVE_ERROR(context, { DATA: { error: 'Something went wrong' } });
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_SAVING', false);
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_SAVE_PHASE', null);
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_SAVE_ERROR', 'Something went wrong');
    });

    it('commits undefined error when DATA is missing', () => {
      const context = makeContext();
      actions.SAVE_ERROR(context, {});
      expect(context.commit).toHaveBeenCalledWith('SET_DRAFT_SAVE_ERROR', undefined);
    });
  });

  describe('COLLAB_ERROR', () => {
    it('logs error and does not throw', () => {
      const context = makeContext();
      expect(() => actions.COLLAB_ERROR(context, { DATA: { error: 'Room full' } })).not.toThrow();
      expect(log.error).toHaveBeenCalled();
    });

    it('handles missing DATA without throwing', () => {
      const context = makeContext();
      expect(() => actions.COLLAB_ERROR(context, {})).not.toThrow();
    });
  });

  describe('YJS_SYNC (no provider)', () => {
    it('returns false when no provider is active', () => {
      const context = makeContext();
      const result = actions.YJS_SYNC(context, { DATA: { step: 0 } });
      expect(result).toBe(false);
      expect(context.commit).not.toHaveBeenCalled();
    });
  });

  describe('YJS_UPDATE (no provider)', () => {
    it('returns false when no provider is active', () => {
      const context = makeContext();
      const result = actions.YJS_UPDATE(context, { DATA: { payload: 'dA==' } });
      expect(result).toBe(false);
    });
  });

  describe('YJS_AWARENESS (no provider)', () => {
    it('returns false when no provider is active', () => {
      const context = makeContext();
      const result = actions.YJS_AWARENESS(context, { DATA: { payload: 'dA==' } });
      expect(result).toBe(false);
      expect(context.commit).not.toHaveBeenCalled();
    });
  });
});
