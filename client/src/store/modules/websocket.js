import Vue from 'vue';
import log from 'loglevel';

import router from '@/router';

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
              OP: 'SET_UUID',
              DATA: state.internalUUID,
            });
          } else {
            state.internalUUID = message.DATA;
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
