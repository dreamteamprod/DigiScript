import Vue from 'vue';
import Vuex from 'vuex';
import createPersistedState from 'vuex-persistedstate';
import log from 'loglevel';

import { makeURL } from '@/js/utils';
import user from '@/store/modules/user/user';
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
        await context.commit('SET_CURRENT_SHOW', showSettings);
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
        await context.dispatch('GET_CURRENT_USER');
        await context.dispatch('GET_CURRENT_RBAC');
      }
      window.location.reload();
    },
  },
  getters: {
    CURRENT_SHOW(state) {
      return state.currentShow;
    },
    IS_ADMIN_USER(state, getters) {
      return getters.CURRENT_USER != null && getters.CURRENT_USER.is_admin;
    },
    IS_SHOW_EDITOR(state, getters) {
      if (getters.IS_ADMIN_USER) {
        return true;
      }
      if (getters.RBAC_ROLES.length === 0) {
        return false;
      }
      if (getters.CURRENT_USER_RBAC == null || !Object.keys(getters.CURRENT_USER_RBAC).includes('shows')) {
        return false;
      }
      const writeMask = getters.RBAC_ROLES.find((x) => x.key === 'WRITE').value;
      return getters.CURRENT_USER != null
        // eslint-disable-next-line no-bitwise
        && (getters.CURRENT_USER_RBAC.shows[0][1] & writeMask) !== 0;
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
