import Vue from 'vue';
import Vuex from 'vuex';
import createPersistedState from 'vuex-persistedstate';
import log from 'loglevel';

import { makeURL } from '@/js/utils';
import user from '@/store/modules/user';
import websocket from './modules/websocket';
import system from './modules/system';
import show from './modules/show';
import script from './modules/script';
import scriptConfig from './modules/scriptConfig';

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
  actions: {
    async GET_SHOW_DETAILS(context) {
      const response = await fetch(`${makeURL('/api/v1/show')}`);
      if (response.ok) {
        const showSettings = await response.json();
        context.commit('SET_CURRENT_SHOW', showSettings);
      } else {
        log.error('Unable to get show details');
      }
    },
    async UPDATE_SHOW(context, showDetails) {
      const response = await fetch(`${makeURL('/api/v1/show')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(showDetails),
      });
      if (response.ok) {
        context.dispatch('GET_SHOW_DETAILS');
        Vue.$toast.success('Updated show!');
      } else {
        log.error('Unable to edit show');
        Vue.$toast.error('Unable to edit show');
      }
    },
    async SHOW_CHANGED(context) {
      if (context.rootGetters.CURRENT_USER != null) {
        const response = await fetch(`${makeURL('/api/v1/auth/validate')}`);
        if (response.status === 401) {
          await context.dispatch('USER_LOGOUT');
        }
      }
      window.location.reload();
    },
  },
  getters: {
    CURRENT_SHOW(state) {
      return state.currentShow;
    },
  },
  modules: {
    websocket,
    system,
    show,
    script,
    scriptConfig,
    user,
  },
  plugins: [
    createPersistedState({
      storage: window.sessionStorage,
      key: 'digiscript',
      paths: ['websocket.internalUUID'],
    }),
  ],
});
