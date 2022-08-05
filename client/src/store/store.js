import Vue from 'vue';
import Vuex from 'vuex';

import websocket from './modules/websocket';
import system from './modules/system';

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    currentShow: null,
  },
  mutations: {
    SET_CURRENT_SHOW(state, show) {
      state.currentShow = show;
    },
  },
  actions: {},
  modules: {
    websocket,
    system,
  },
});
