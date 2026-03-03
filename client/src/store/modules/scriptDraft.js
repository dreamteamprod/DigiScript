/**
 * Vuex module for collaborative script editing draft state.
 *
 * Tracks the connection state to a collaborative editing room,
 * the Yjs document and provider instances, and collaborator presence.
 *
 * IMPORTANT: The Y.Doc and ScriptDocProvider instances are stored outside
 * of Vuex reactive state (as module-level variables). Vue 2's reactivity
 * system deeply observes all objects in state, adding getters/setters to
 * every property. For complex library objects like Y.Doc, this causes Vue
 * to track internal Yjs properties as reactive dependencies — leading to
 * infinite render loops when Y.Doc internals change during transactions.
 */

import Vue from 'vue';
import * as Y from 'yjs';
import log from 'loglevel';

import ScriptDocProvider from '@/utils/yjs/ScriptDocProvider';

/**
 * Non-reactive storage for Y.Doc and provider instances.
 * These must NOT be stored in Vuex state because Vue 2 would make them
 * deeply reactive, breaking Yjs internal state management.
 *
 * @type {import('yjs').Doc|null}
 */
let _ydoc = null;

/** @type {ScriptDocProvider|null} */
let _provider = null;

/** @type {number|null} Interval ID for the sync-polling loop */
let _syncIntervalId = null;

/** @type {number|null} Timeout ID for the sync-failure watchdog */
let _syncTimeoutId = null;

export default {
  state: {
    /** @type {number|null} The revision ID of the active room */
    roomId: null,

    /** @type {boolean} Whether we are connected to a collab room */
    isConnected: false,

    /** @type {boolean} Whether the initial sync from the server is complete */
    isSynced: false,

    /** @type {boolean} Whether there are unsaved changes in the draft */
    isDraft: false,

    /** @type {string|null} ISO timestamp of last save */
    lastSavedAt: null,

    /** @type {Array<{user_id: number, username: string, role: string}>} */
    collaborators: [],

    /** @type {Object<number, {page: number|null, lineIndex: number|null, username: string}>} */
    awarenessStates: {},

    /** @type {boolean} Whether a save is currently in progress */
    isSaving: false,

    /** @type {string|null} Current save phase ('validating', 'persisting', 'finalizing') */
    savePhase: null,

    /** @type {object|null} Last save error */
    saveError: null,

    /** @type {number} Pages saved so far during the current save (0 = starting) */
    savePage: 0,

    /** @type {number} Total pages to save in the current save operation */
    saveTotalPages: 0,
  },

  mutations: {
    SET_DRAFT_ROOM(state, { roomId }) {
      state.roomId = roomId;
    },

    SET_DRAFT_CONNECTED(state, value) {
      state.isConnected = value;
    },

    SET_DRAFT_SYNCED(state, value) {
      state.isSynced = value;
    },

    SET_DRAFT_DIRTY(state, value) {
      state.isDraft = value;
    },

    SET_DRAFT_LAST_SAVED(state, timestamp) {
      state.lastSavedAt = timestamp;
    },

    SET_DRAFT_COLLABORATORS(state, collaborators) {
      state.collaborators = collaborators;
    },

    SET_AWARENESS_STATE(state, { userId, awarenessState }) {
      Vue.set(state.awarenessStates, userId, awarenessState);
    },

    REMOVE_AWARENESS_STATE(state, userId) {
      Vue.delete(state.awarenessStates, userId);
    },

    SET_DRAFT_SAVING(state, value) {
      state.isSaving = value;
    },

    SET_DRAFT_SAVE_PHASE(state, phase) {
      state.savePhase = phase;
    },

    SET_DRAFT_SAVE_ERROR(state, error) {
      state.saveError = error;
    },

    SET_SAVE_PROGRESS(state, { page, total }) {
      state.savePage = page;
      state.saveTotalPages = total;
    },

    CLEAR_DRAFT_STATE(state) {
      state.roomId = null;
      state.isConnected = false;
      state.isSynced = false;
      state.isDraft = false;
      state.lastSavedAt = null;
      state.collaborators = [];
      state.awarenessStates = {};
      state.isSaving = false;
      state.savePhase = null;
      state.saveError = null;
      state.savePage = 0;
      state.saveTotalPages = 0;
      _ydoc = null;
      _provider = null;
    },
  },

  actions: {
    /**
     * Join a collaborative editing room for a script revision.
     * Creates a Y.Doc and ScriptDocProvider, connects to the server.
     *
     * @param {object} context - Vuex action context
     * @param {object} params
     * @param {number} params.revisionId - Script revision to edit
     * @param {string} [params.role='editor'] - 'editor' or 'viewer'
     */
    async JOIN_DRAFT_ROOM(context, { revisionId, role = 'editor' }) {
      // Leave existing room first
      if (_provider) {
        await context.dispatch('LEAVE_DRAFT_ROOM');
      }

      const ydoc = new Y.Doc();
      const provider = new ScriptDocProvider(ydoc, revisionId, { role });

      // Store instances outside reactive state
      _ydoc = ydoc;
      _provider = provider;

      context.commit('SET_DRAFT_ROOM', { roomId: revisionId });

      // Cancel any stale timers from a previous join before creating new ones
      if (_syncIntervalId) {
        clearInterval(_syncIntervalId);
        _syncIntervalId = null;
      }
      if (_syncTimeoutId) {
        clearTimeout(_syncTimeoutId);
        _syncTimeoutId = null;
      }

      // Listen for sync completion
      _syncIntervalId = setInterval(() => {
        if (provider.synced) {
          log.debug('ScriptDraft: Sync detected via polling; clearing timer');
          context.commit('SET_DRAFT_SYNCED', true);
          context.commit('SET_DRAFT_CONNECTED', true);
          clearInterval(_syncIntervalId);
          _syncIntervalId = null;
        }
      }, 100);

      // Watchdog: log an error only if this is still the active provider
      _syncTimeoutId = setTimeout(() => {
        clearInterval(_syncIntervalId);
        _syncIntervalId = null;
        _syncTimeoutId = null;
        log.debug(
          `ScriptDraft: Sync timeout fired (provider is ${provider === _provider ? 'current' : 'stale'}); synced=${provider.synced}`
        );
        if (provider === _provider && !provider.synced) {
          log.error('ScriptDraft: Sync timeout after 10 seconds');
        }
      }, 10000);

      provider.connect();
      log.debug(`ScriptDraft: Provider connect() called for revision ${revisionId}`);
      log.info(`ScriptDraft: Joined room for revision ${revisionId} as ${role}`);
    },

    /**
     * Leave the current collaborative editing room.
     */
    async LEAVE_DRAFT_ROOM(context) {
      log.debug(
        `ScriptDraft: Cancelling sync timers (interval=${_syncIntervalId}, timeout=${_syncTimeoutId})`
      );
      if (_syncIntervalId) {
        clearInterval(_syncIntervalId);
        _syncIntervalId = null;
      }
      if (_syncTimeoutId) {
        clearTimeout(_syncTimeoutId);
        _syncTimeoutId = null;
      }

      if (_provider) {
        _provider.destroy();
      }

      context.commit('CLEAR_DRAFT_STATE');
      log.info('ScriptDraft: Left draft room');
    },

    /**
     * Handle a YJS_SYNC message: apply to provider, update synced state.
     *
     * @param {object} context
     * @param {object} message - The WebSocket message
     * @returns {boolean} Whether the message was handled
     */
    YJS_SYNC(context, message) {
      if (!_provider) return false;
      const handled = _provider.applySync(message.DATA);
      if (handled && _provider.synced && !context.state.isSynced) {
        context.commit('SET_DRAFT_SYNCED', true);
        context.commit('SET_DRAFT_CONNECTED', true);
      }
      return handled;
    },

    /**
     * Handle a YJS_UPDATE message: apply remote doc update to provider.
     *
     * @param {object} context
     * @param {object} message - The WebSocket message
     * @returns {boolean} Whether the message was handled
     */
    YJS_UPDATE(context, message) {
      if (!_provider) return false;
      return _provider.applyUpdate(message.DATA);
    },

    /**
     * Handle a YJS_AWARENESS message: decode and commit awareness state.
     *
     * @param {object} context
     * @param {object} message - The WebSocket message
     * @returns {boolean|object} Whether the message was handled
     */
    YJS_AWARENESS(context, message) {
      if (!_provider) return false;
      const handled = _provider.applyAwareness(message.DATA);
      if (handled && typeof handled === 'object' && handled.type === 'AWARENESS') {
        const state = handled.state;
        if (state?.userId != null) {
          if (state.page === null && state.lineIndex === null) {
            context.commit('REMOVE_AWARENESS_STATE', state.userId);
          } else {
            context.commit('SET_AWARENESS_STATE', { userId: state.userId, awarenessState: state });
          }
        }
      }
      return handled;
    },

    /**
     * Handle a ROOM_MEMBERS message: update collaborator list.
     *
     * @param {object} context
     * @param {object} message - The WebSocket message
     */
    ROOM_MEMBERS(context, message) {
      context.commit('SET_DRAFT_COLLABORATORS', message.DATA?.members || []);
    },

    /**
     * Handle a ROOM_CLOSED message: leave the draft room.
     *
     * @param {object} context
     */
    ROOM_CLOSED(context) {
      context.dispatch('LEAVE_DRAFT_ROOM');
    },

    /**
     * Handle a SCRIPT_SAVED message: clear saving state and record timestamp.
     *
     * @param {object} context
     * @param {object} message - The WebSocket message
     */
    SCRIPT_SAVED(context, message) {
      context.commit('SET_DRAFT_SAVING', false);
      context.commit('SET_DRAFT_SAVE_PHASE', null);
      context.commit('SET_DRAFT_SAVE_ERROR', null);
      context.commit('SET_DRAFT_DIRTY', false);
      const timestamp = message.DATA?.last_saved_at;
      if (timestamp) context.commit('SET_DRAFT_LAST_SAVED', timestamp);
    },

    /**
     * Handle a SAVE_PROGRESS message: update save progress state.
     *
     * @param {object} context
     * @param {object} message - The WebSocket message
     */
    SAVE_PROGRESS(context, message) {
      context.commit('SET_DRAFT_SAVING', true);
      context.commit('SET_SAVE_PROGRESS', message.DATA);
    },

    /**
     * Handle a SAVE_ERROR message: clear saving state and record error.
     *
     * @param {object} context
     * @param {object} message - The WebSocket message
     */
    SAVE_ERROR(context, message) {
      context.commit('SET_DRAFT_SAVING', false);
      context.commit('SET_DRAFT_SAVE_PHASE', null);
      context.commit('SET_DRAFT_SAVE_ERROR', message.DATA?.error);
    },

    /**
     * Handle a COLLAB_ERROR message: log the error from the server.
     *
     * @param {object} _context
     * @param {object} message - The WebSocket message
     */
    COLLAB_ERROR(_context, message) {
      log.error('Collab error received:', message.DATA?.error);
    },
  },

  getters: {
    /** @returns {boolean} Whether a collaborative editing session is active */
    IS_DRAFT_ACTIVE(state) {
      return state.roomId !== null && state.isConnected;
    },

    /**
     * @returns {import('yjs').Doc|null} The Y.Doc instance (non-reactive)
     *
     * NOTE: `state.roomId` is accessed intentionally to create a reactive
     * dependency. Without it, Vue/Vuex caches this getter permanently (since
     * `_ydoc` is a non-reactive module variable). After LEAVE_DRAFT_ROOM +
     * JOIN_DRAFT_ROOM, `roomId` changes, busting the cache so the new Y.Doc
     * instance is returned to all components.
     */
    DRAFT_YDOC(state) {
      state.roomId; // reactive dependency — forces re-evaluation on room change
      return _ydoc;
    },

    /** @returns {ScriptDocProvider|null} The provider instance (non-reactive) */
    DRAFT_PROVIDER(state) {
      state.roomId; // reactive dependency — see DRAFT_YDOC comment
      return _provider;
    },

    /** @returns {import('yjs').Map|null} The Y.Doc pages map */
    DRAFT_PAGES(state) {
      state.roomId; // reactive dependency — see DRAFT_YDOC comment
      if (!_ydoc) return null;
      return _ydoc.getMap('pages');
    },

    /** @returns {import('yjs').Map|null} The Y.Doc meta map */
    DRAFT_META(state) {
      state.roomId; // reactive dependency — see DRAFT_YDOC comment
      if (!_ydoc) return null;
      return _ydoc.getMap('meta');
    },

    /** @returns {import('yjs').Array|null} The deleted line IDs array */
    DRAFT_DELETED_LINE_IDS(state) {
      state.roomId; // reactive dependency — see DRAFT_YDOC comment
      if (!_ydoc) return null;
      return _ydoc.getArray('deleted_line_ids');
    },

    /** @returns {boolean} Whether a save is in progress */
    IS_DRAFT_SAVING(state) {
      return state.isSaving;
    },

    /** @returns {string|null} Current save phase */
    DRAFT_SAVE_PHASE(state) {
      return state.savePhase;
    },

    /** @returns {{page: number, total: number}} Current save progress */
    DRAFT_SAVE_PROGRESS(state) {
      return { page: state.savePage, total: state.saveTotalPages };
    },

    /** @returns {boolean} Whether there are unsaved changes in the draft */
    IS_DRAFT_DIRTY(state) {
      return state.isDraft;
    },

    /** @returns {boolean} Whether initial sync is complete */
    IS_DRAFT_SYNCED(state) {
      return state.isSynced;
    },

    /** @returns {Array} List of collaborators in the room */
    DRAFT_COLLABORATORS(state) {
      return state.collaborators;
    },

    /** @returns {Object} Awareness states keyed by userId */
    DRAFT_AWARENESS_STATES(state) {
      return state.awarenessStates;
    },

    /**
     * Map of "page:lineIndex" → array of users editing that line.
     * Used by ScriptLineViewer to show editing indicators.
     *
     * @returns {Object<string, Array<{userId: number, username: string}>>}
     */
    DRAFT_LINE_EDITORS(state) {
      const result = {};
      for (const [userId, awareness] of Object.entries(state.awarenessStates)) {
        if (awareness.page != null && awareness.lineIndex != null) {
          const key = `${awareness.page}:${awareness.lineIndex}`;
          if (!result[key]) result[key] = [];
          result[key].push({
            userId: Number(userId),
            username: awareness.username || 'Unknown',
          });
        }
      }
      return result;
    },
  },
};
