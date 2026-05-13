import Vue from 'vue';
import log from 'loglevel';
import { debounce } from 'lodash';
import type { Module } from 'vuex';

import router from '@/router';
import type { RootState } from '@/types/store';

interface WebsocketState {
  isConnected: boolean;
  message: string;
  reconnectError: boolean;
  internalUUID: string | null;
  errorCount: number;
  error: boolean;
  authenticated: boolean;
  authenticationInProgress: boolean;
  pendingAuthentication: boolean;
  newConnection: boolean;
  authSucceeded: boolean;
}

const VueToast = Vue as typeof Vue & {
  $toast: {
    success: (m: string) => void;
    error: (m: string) => void;
    info: (m: string) => void;
  };
};

const settingsToast = debounce(
  () => {
    VueToast.$toast.info('Settings synced from server');
  },
  1000,
  { leading: true, trailing: false }
);

const module: Module<WebsocketState, RootState> = {
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
    SOCKET_ONOPEN(state: WebsocketState, event: Event) {
      Vue.prototype.$socket = (event as { currentTarget: unknown }).currentTarget;
      state.isConnected = true;
      state.error = false;
      state.reconnectError = false;
      if (state.errorCount !== 0) {
        VueToast.$toast.success(`Websocket reconnected after ${state.errorCount} attempts`);
        state.errorCount = 0;
        if (router.currentRoute.path !== '/') {
          window.location.reload();
        }
      }
    },
    SOCKET_ONCLOSE(state: WebsocketState) {
      state.isConnected = false;
      state.authenticated = false;
    },
    SOCKET_ONERROR(state: WebsocketState) {
      state.error = true;
    },
    SOCKET_ONMESSAGE(state: WebsocketState, message: { OP: string; DATA: unknown }) {
      state.message = JSON.stringify(message);
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
            state.internalUUID = message.DATA as string;
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
          if (router.currentRoute.path !== '/live') {
            router.push('/live');
          }
          break;
        case 'STOP_SHOW':
          if (router.currentRoute.path !== '/') {
            router.push('/');
          }
          break;
        case 'RELOAD_CLIENT':
          window.location.reload();
          break;
        default:
          log.error(`Unknown OP received from websocket: ${message.OP}`);
      }
    },
    SOCKET_RECONNECT(state: WebsocketState, count: number) {
      if (state.errorCount === 0) {
        VueToast.$toast.error('Websocket connection lost');
      }
      state.errorCount = count;
      state.authenticated = false;
    },
    SOCKET_RECONNECT_ERROR(state: WebsocketState) {
      state.reconnectError = true;
    },
    CLEAR_WS_AUTHENTICATION(state: WebsocketState) {
      state.authenticated = false;
      state.authSucceeded = false;
      state.pendingAuthentication = true;
    },
    SET_WS_AUTHENTICATION_IN_PROGRESS(state: WebsocketState, value: boolean) {
      state.authenticationInProgress = value;
    },
    CLEAR_PENDING_AUTHENTICATION(state: WebsocketState) {
      state.pendingAuthentication = false;
    },
    CLEAR_NEW_CONNECTION(state: WebsocketState) {
      state.newConnection = false;
    },
    CLEAR_AUTH_SUCCEEDED(state: WebsocketState) {
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
      if (
        context.state.newConnection &&
        !context.state.pendingAuthentication &&
        !context.state.authenticationInProgress &&
        !context.state.authSucceeded
      ) {
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
      if (
        !context.rootGetters.AUTH_TOKEN ||
        !Vue.prototype.$socket ||
        Vue.prototype.$socket.readyState !== WebSocket.OPEN
      ) {
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
      if (
        !context.rootGetters.AUTH_TOKEN ||
        !Vue.prototype.$socket ||
        Vue.prototype.$socket.readyState !== WebSocket.OPEN
      ) {
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
    WEBSOCKET_HEALTHY(state: WebsocketState) {
      return !state.error && state.isConnected && !state.reconnectError && state.errorCount === 0;
    },
    INTERNAL_UUID(state: WebsocketState) {
      return state.internalUUID;
    },
    WEBSOCKET_HAS_PENDING_OPERATIONS(state: WebsocketState) {
      return state.pendingAuthentication || state.newConnection || state.authSucceeded;
    },
  },
};

export default module;
