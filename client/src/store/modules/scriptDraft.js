/**
 * Vuex module for collaborative script editing draft state.
 *
 * Tracks the connection state to a collaborative editing room,
 * the Yjs document and provider instances, and collaborator presence.
 */

import Vue from 'vue';
import * as Y from 'yjs';
import log from 'loglevel';

import ScriptDocProvider from '@/utils/yjs/ScriptDocProvider';

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

    /**
     * @type {import('yjs').Doc|null}
     * The Yjs document instance. Not persisted to localStorage.
     */
    ydoc: null,

    /**
     * @type {ScriptDocProvider|null}
     * The Yjs provider instance. Not persisted to localStorage.
     */
    provider: null,
  },

  mutations: {
    SET_DRAFT_ROOM(state, { roomId, ydoc, provider }) {
      state.roomId = roomId;
      state.ydoc = ydoc;
      state.provider = provider;
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
      state.ydoc = null;
      state.provider = null;
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
      if (context.state.provider) {
        await context.dispatch('LEAVE_DRAFT_ROOM');
      }

      const ydoc = new Y.Doc();
      const provider = new ScriptDocProvider(ydoc, revisionId, { role });

      context.commit('SET_DRAFT_ROOM', {
        roomId: revisionId,
        ydoc,
        provider,
      });

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
      const { provider } = context.state;
      if (provider) {
        provider.destroy();
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
      const { provider } = context.state;
      if (!provider) return false;

      const handled = provider.handleMessage(message);

      // Check if sync status changed
      if (handled && provider.synced && !context.state.isSynced) {
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

    /** @returns {import('yjs').Doc|null} The Y.Doc instance */
    DRAFT_YDOC(state) {
      return state.ydoc;
    },

    /** @returns {import('yjs').Map|null} The Y.Doc pages map */
    DRAFT_PAGES(state) {
      if (!state.ydoc) return null;
      return state.ydoc.getMap('pages');
    },

    /** @returns {import('yjs').Map|null} The Y.Doc meta map */
    DRAFT_META(state) {
      if (!state.ydoc) return null;
      return state.ydoc.getMap('meta');
    },

    /** @returns {import('yjs').Array|null} The deleted line IDs array */
    DRAFT_DELETED_LINE_IDS(state) {
      if (!state.ydoc) return null;
      return state.ydoc.getArray('deleted_line_ids');
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
