import Vue from 'vue';
import log from 'loglevel';
import { debounce } from 'lodash';

import router from '@/router';

const settingsToast = debounce(() => {
  Vue.$toast.info('Settings synced from server');
}, 1000, { leading: true, trailing: false });

export default {
  state: {
    isConnected: false,
    message: '',
    reconnectError: false,
    internalUUID: null,
    errorCount: 0,
    error: false,
    authenticated: false,
    authenticationInProgress: false,
    pendingAuthentication: false,
    newConnection: false,
    authSucceeded: false,
  },
  mutations: {
    SOCKET_ONOPEN(state, event) {
      Vue.prototype.$socket = event.currentTarget;
      state.isConnected = true;
      state.error = false;
      state.reconnectError = false;
      if (state.errorCount !== 0) {
        Vue.$toast.success(`Websocket reconnected after ${state.errorCount} attempts`);
        state.errorCount = 0;
        if (router.currentRoute !== '/') {
          window.location.reload();
        }
      }
    },
    SOCKET_ONCLOSE(state, event) {
      state.isConnected = false;
      state.authenticated = false;
    },
    SOCKET_ONERROR(state, event) {
      state.error = true;
    },
    // default handler called for all methods
    SOCKET_ONMESSAGE(state, message) {
      state.message = message;
      switch (message.OP) {
        case 'SET_UUID':
          if (state.internalUUID != null) {
            log.debug('Reconnecting to WebSocket with existing UUID:', state.internalUUID);
            Vue.prototype.$socket.sendObj({
              OP: 'REFRESH_CLIENT',
              DATA: state.internalUUID,
            });
          } else {
            log.debug('Connecting to WebSocket as new client, with UUID:', message.DATA);
            state.internalUUID = message.DATA;
            state.newConnection = true;
          }
          if (!state.authenticated && !state.authenticationInProgress) {
            state.pendingAuthentication = true;
          }
          break;
        case 'WS_AUTH_SUCCESS':
          state.authenticated = true;
          state.authenticationInProgress = false;
          state.pendingAuthentication = false;
          state.authSucceeded = true;
          log.info('WebSocket authenticated successfully');
          break;
        case 'WS_AUTH_ERROR':
          state.authenticated = false;
          state.authenticationInProgress = false;
          state.pendingAuthentication = false;
          log.error(`WebSocket authentication error: ${message.DATA}`);
          break;
        case 'WS_TOKEN_REFRESH_SUCCESS':
          log.info('WebSocket token refreshed successfully');
          break;
        case 'SETTINGS_CHANGED':
          break;
        case 'GET_CAST_LIST':
          break;
        case 'START_SHOW':
          if (router.currentRoute !== '/live') {
            router.push('/live');
          }
          break;
        case 'STOP_SHOW':
          if (router.currentRoute !== '/') {
            router.push('/');
          }
          break;
        case 'RELOAD_CLIENT':
          window.location.reload();
          break;
        case 'COMPRESSED_SCRIPT_DATA':
          if (message.DATA && message.DATA.compressed_data) {
            this.context.dispatch('script/LOAD_COMPRESSED_SCRIPT_DATA', message.DATA.compressed_data, { root: true });
          }
          break;
        default:
          log.error(`Unknown OP received from websocket: ${message.OP}`);
      }
    },
    // mutations for reconnect methods
    SOCKET_RECONNECT(state, count) {
      if (state.errorCount === 0) {
        Vue.$toast.error('Websocket connection lost');
      }
      state.errorCount = count;
      state.authenticated = false;
    },
    SOCKET_RECONNECT_ERROR(state) {
      state.reconnectError = true;
    },
    CLEAR_WS_AUTHENTICATION(state) {
      state.authenticated = false;
      state.authSucceeded = false;
      state.pendingAuthentication = true;
    },
    SET_WS_AUTHENTICATION_IN_PROGRESS(state, value) {
      state.authenticationInProgress = value;
    },
    CLEAR_PENDING_AUTHENTICATION(state) {
      state.pendingAuthentication = false;
    },
    CLEAR_NEW_CONNECTION(state) {
      state.newConnection = false;
    },
    CLEAR_AUTH_SUCCEEDED(state) {
      state.authSucceeded = false;
    },
  },
  actions: {
    async WS_SETTINGS_CHANGED(context, payload) {
      await context.dispatch('UPDATE_SETTINGS', payload.DATA);
      settingsToast();
    },
    async CHECK_WEBSOCKET_STATE(context) {
      if (context.state.pendingAuthentication && context.rootGetters.AUTH_TOKEN) {
        await context.dispatch('AUTHENTICATE_WEBSOCKET');
      }
      if (context.state.authSucceeded) {
        await context.dispatch('HANDLE_WS_AUTH_SUCCESS');
        await context.commit('CLEAR_AUTH_SUCCEEDED');
      }
      if (context.state.newConnection
          && !context.state.pendingAuthentication
          && !context.state.authenticationInProgress
          && !context.state.authSucceeded) {
        if (Vue.prototype.$socket && Vue.prototype.$socket.readyState === WebSocket.OPEN) {
          Vue.prototype.$socket.sendObj({
            OP: 'NEW_CLIENT',
            DATA: {},
          });
          await context.commit('CLEAR_NEW_CONNECTION');
        }
      }
    },
    async AUTHENTICATE_WEBSOCKET(context) {
      if (!context.rootGetters.AUTH_TOKEN || !Vue.prototype.$socket
          || Vue.prototype.$socket.readyState !== WebSocket.OPEN) {
        return;
      }
      await context.commit('SET_WS_AUTHENTICATION_IN_PROGRESS', true);
      await context.commit('CLEAR_PENDING_AUTHENTICATION');
      Vue.prototype.$socket.sendObj({
        OP: 'AUTHENTICATE',
        DATA: {
          token: context.rootGetters.AUTH_TOKEN,
        },
      });
      log.debug('Sent WebSocket authentication request');
    },
    async HANDLE_WS_AUTH_SUCCESS(context) {
      // After successful authentication, register as a new client if this is a new connection
      if (context.state.newConnection) {
        if (Vue.prototype.$socket && Vue.prototype.$socket.readyState === WebSocket.OPEN) {
          Vue.prototype.$socket.sendObj({
            OP: 'NEW_CLIENT',
            DATA: {},
          });
          await context.commit('CLEAR_NEW_CONNECTION');
        }
      }
    },
    async REFRESH_WEBSOCKET_TOKEN(context) {
      if (!context.rootGetters.AUTH_TOKEN || !Vue.prototype.$socket
          || Vue.prototype.$socket.readyState !== WebSocket.OPEN) {
        return;
      }
      Vue.prototype.$socket.sendObj({
        OP: 'REFRESH_TOKEN',
        DATA: {
          token: context.rootGetters.AUTH_TOKEN,
        },
      });
      log.debug('Sent WebSocket token refresh');
    },
  },
  getters: {
    WEBSOCKET_HEALTHY(state) {
      return !state.error && state.isConnected && !state.reconnectError && state.errorCount === 0;
    },
    INTERNAL_UUID(state) {
      return state.internalUUID;
    },
    WEBSOCKET_HAS_PENDING_OPERATIONS(state) {
      return state.pendingAuthentication || state.newConnection || state.authSucceeded;
    },
  },
};
