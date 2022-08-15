import * as $ from 'jquery';

import { makeURL } from '@/js/utils';

export default {
  state: {
    settings: {},
    availableShows: [],
  },
  mutations: {
    UPDATE_SETTINGS(state, settings) {
      state.settings = settings;
    },
    UPDATE_SHOWS(state, shows) {
      state.availableShows = shows;
    },
  },
  actions: {
    async UPDATE_SETTINGS(context, payload) {
      context.commit('UPDATE_SETTINGS', payload);
      await context.dispatch('SETTINGS_CHANGED');
    },
    async SETTINGS_CHANGED(context) {
      if (context.state.settings.current_show) {
        const currShow = context.state.settings.current_show;
        if (!context.state.currentShow || context.state.currentShow.id !== currShow) {
          const response = await fetch(`${makeURL('/api/v1/show')}`);
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
};
