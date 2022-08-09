import Vue from 'vue';

export default {
  state: {
    isConnected: false,
    message: '',
    reconnectError: false,
    internalUUID: null,
  },
  mutations: {
    SOCKET_ONOPEN(state, event) {
      Vue.prototype.$socket = event.currentTarget;
      state.isConnected = true;
    },
    SOCKET_ONCLOSE(state, event) {
      state.isConnected = false;
    },
    SOCKET_ONERROR(state, event) {
      console.error(state, event);
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
        case 'NOOP':
          break;
        default:
          console.error(`Unknown OP received from websocket: ${message.OP}`);
      }
    },
    // mutations for reconnect methods
    SOCKET_RECONNECT(state, count) {
      console.info(state, count);
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
};
