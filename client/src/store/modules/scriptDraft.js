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

    CLEAR_DRAFT_STATE(state) {
      state.roomId = null;
      state.isConnected = false;
      state.isSynced = false;
      state.isDraft = false;
      state.lastSavedAt = null;
      state.collaborators = [];
      state.awarenessStates = {};
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

      // Listen for sync completion
      const checkSynced = setInterval(() => {
        if (provider.synced) {
          context.commit('SET_DRAFT_SYNCED', true);
          context.commit('SET_DRAFT_CONNECTED', true);
          clearInterval(checkSynced);
        }
      }, 100);

      // Stop checking after 10 seconds (timeout)
      setTimeout(() => {
        clearInterval(checkSynced);
        if (!provider.synced) {
          log.error('ScriptDraft: Sync timeout after 10 seconds');
        }
      }, 10000);

      provider.connect();
      log.info(`ScriptDraft: Joined room for revision ${revisionId} as ${role}`);
    },

    /**
     * Leave the current collaborative editing room.
     */
    async LEAVE_DRAFT_ROOM(context) {
      if (_provider) {
        _provider.destroy();
      }

      context.commit('CLEAR_DRAFT_STATE');
      log.info('ScriptDraft: Left draft room');
    },

    /**
     * Handle an incoming WebSocket message that might be for the draft provider.
     * Called from the SOCKET_ONMESSAGE mutation or action.
     *
     * @param {object} context
     * @param {object} message - The WebSocket message
     * @returns {boolean} Whether the message was handled
     */
    HANDLE_DRAFT_MESSAGE(context, message) {
      if (!_provider) return false;

      const handled = _provider.handleMessage(message);

      // Check if sync status changed
      if (handled && _provider.synced && !context.state.isSynced) {
        context.commit('SET_DRAFT_SYNCED', true);
        context.commit('SET_DRAFT_CONNECTED', true);
      }

      // Handle structured responses from the provider
      if (handled && typeof handled === 'object') {
        if (handled.type === 'ROOM_MEMBERS') {
          context.commit('SET_DRAFT_COLLABORATORS', handled.members);
        } else if (handled.type === 'AWARENESS') {
          const state = handled.state;
          if (state && state.userId != null) {
            if (state.page === null && state.lineIndex === null) {
              context.commit('REMOVE_AWARENESS_STATE', state.userId);
            } else {
              context.commit('SET_AWARENESS_STATE', {
                userId: state.userId,
                awarenessState: state,
              });
            }
          }
        }
      }

      return handled;
    },
  },

  getters: {
    /** @returns {boolean} Whether a collaborative editing session is active */
    IS_DRAFT_ACTIVE(state) {
      return state.roomId !== null && state.isConnected;
    },

    /** @returns {import('yjs').Doc|null} The Y.Doc instance (non-reactive) */
    DRAFT_YDOC() {
      return _ydoc;
    },

    /** @returns {ScriptDocProvider|null} The provider instance (non-reactive) */
    DRAFT_PROVIDER() {
      return _provider;
    },

    /** @returns {import('yjs').Map|null} The Y.Doc pages map */
    DRAFT_PAGES() {
      if (!_ydoc) return null;
      return _ydoc.getMap('pages');
    },

    /** @returns {import('yjs').Map|null} The Y.Doc meta map */
    DRAFT_META() {
      if (!_ydoc) return null;
      return _ydoc.getMap('meta');
    },

    /** @returns {import('yjs').Array|null} The deleted line IDs array */
    DRAFT_DELETED_LINE_IDS() {
      if (!_ydoc) return null;
      return _ydoc.getArray('deleted_line_ids');
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
