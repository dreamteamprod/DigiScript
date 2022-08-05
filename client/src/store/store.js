import Vue from 'vue';
import Vuex from 'vuex';

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    socket: {
      isConnected: false,
      message: '',
      reconnectError: false,
      internalUUID: null,
    },
    system: {
      settings: {},
      availableShows: [],
    },
    currentShow: null,
  },
  mutations: {
    SOCKET_ONOPEN(state, event) {
      Vue.prototype.$socket = event.currentTarget;
      state.socket.isConnected = true;
    },
    SOCKET_ONCLOSE(state, event) {
      state.socket.isConnected = false;
    },
    SOCKET_ONERROR(state, event) {
      console.error(state, event);
    },
    // default handler called for all methods
    SOCKET_ONMESSAGE(state, message) {
      state.socket.message = message;
      switch (message.OP) {
        case 'SET_UUID':
          state.socket.internalUUID = message.DATA;
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
      state.socket.reconnectError = true;
    },
    UPDATE_SETTINGS(state, settings) {
      state.system.settings = settings;
    },
    UPDATE_SHOWS(state, shows) {
      state.system.availableShows = shows;
    },
    SET_CURRENT_SHOW(state, show) {
      state.currentShow = show;
    },
  },
  actions: {
    async SETTINGS_CHANGED(context) {
      if (context.state.system.settings.current_show) {
        const currShow = context.state.system.settings.current_show;
        if (!context.state.currentShow || context.state.currentShow.id !== currShow) {
          const response = await fetch(`${utils.makeURL('/api/v1/show')}?${$.param({
            show_id: currShow,
          })}`);
          if (response.ok) {
            const show = await response.json();
            context.commit('SET_CURRENT_SHOW', show);
          } else {
            console.error('Unable to set current show');
          }
        }
      }
    },
  },
});
