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
    },
    SOCKET_ONERROR(state, event) {
      state.error = false;
    },
    // default handler called for all methods
    SOCKET_ONMESSAGE(state, message) {
      state.message = message;
      switch (message.OP) {
        case 'SET_UUID':
          if (state.internalUUID != null) {
            Vue.prototype.$socket.sendObj({
              OP: 'REFRESH_CLIENT',
              DATA: state.internalUUID,
            });
          } else {
            state.internalUUID = message.DATA;
            Vue.prototype.$socket.sendObj({
              OP: 'NEW_CLIENT',
              DATA: {},
            });
          }
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
    },
    SOCKET_RECONNECT_ERROR(state) {
      state.reconnectError = true;
    },
  },
  actions: {
    async WS_SETTINGS_CHANGED(context, payload) {
      await context.dispatch('UPDATE_SETTINGS', payload.DATA);
      settingsToast();
    },
  },
  getters: {
    WEBSOCKET_HEALTHY(state) {
      return !state.error && state.isConnected && !state.reconnectError && state.errorCount === 0;
    },
    INTERNAL_UUID(state) {
      return state.internalUUID;
    },
  },
};
