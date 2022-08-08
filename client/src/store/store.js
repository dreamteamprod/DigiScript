import Vue from 'vue';
import Vuex from 'vuex';

import websocket from './modules/websocket';
import system from './modules/system';
import show from './modules/show';

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    currentShow: null,
  },
  mutations: {
    SET_CURRENT_SHOW(state, currShow) {
      state.currentShow = currShow;
    },
  },
  actions: {},
  modules: {
    websocket,
    system,
    show,
  },
});
