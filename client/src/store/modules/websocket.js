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
          state.internalUUID = message.DATA;
          break;
        case 'SETTINGS_CHANGED':
          state.system.settings = message.DATA;
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
};
