import router from "@/router";
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
    async GET_SETTINGS(context) {
      const response = await fetch(makeURL('/api/v1/settings'));
      if (response.ok) {
        const settings = await response.json();
        await context.dispatch('UPDATE_SETTINGS', settings);
      } else {
        console.error('Unable to fetch settings');
      }
    },
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
      } else {
        context.commit('SET_CURRENT_SHOW', null);
        context.commit('CLEAR_CURRENT_SHOW');
        if (router.currentRoute.path !== '/') {
          router.push('/');
        }
      }
    },
  },
};
