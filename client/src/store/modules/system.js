import log from 'loglevel';

import router from '@/router';
import { makeURL } from '@/js/utils';

export default {
  state: {
    settings: {},
    availableShows: [],
    rawSettings: {},
    rbacRoles: [],
  },
  mutations: {
    UPDATE_SETTINGS(state, settings) {
      state.settings = settings;
    },
    UPDATE_SHOWS(state, shows) {
      state.availableShows = shows;
    },
    UPDATE_RAW_SETTINGS(state, settings) {
      state.rawSettings = settings;
    },
    UPDATE_RBAC_ROLES(state, rbac) {
      state.rbacRoles = rbac;
    },
  },
  actions: {
    async GET_RAW_SETTINGS(context) {
      const response = await fetch(`${makeURL('/api/v1/settings/raw')}`);
      if (response.ok) {
        const rawSettings = await response.json();
        await context.commit('UPDATE_RAW_SETTINGS', rawSettings);
      } else {
        log.error('Unable to get system settings');
      }
    },
    async GET_SETTINGS(context) {
      const response = await fetch(makeURL('/api/v1/settings'));
      if (response.ok) {
        const settings = await response.json();
        await context.dispatch('UPDATE_SETTINGS', settings);
      } else {
        log.error('Unable to fetch settings');
      }
    },
    async UPDATE_SETTINGS(context, payload) {
      context.commit('UPDATE_SETTINGS', payload);
      await context.dispatch('SETTINGS_CHANGED');
    },
    async SETTINGS_CHANGED(context) {
      await context.dispatch('GET_RAW_SETTINGS');

      if (context.state.settings.current_show) {
        const currShow = context.state.settings.current_show;
        if (!context.state.currentShow || context.state.currentShow.id !== currShow) {
          const response = await fetch(`${makeURL('/api/v1/show')}`);
          if (response.ok) {
            const show = await response.json();
            context.commit('SET_CURRENT_SHOW', show);
          } else {
            log.error('Unable to set current show');
          }
        }
      } else {
        context.commit('SET_CURRENT_SHOW', null);
        context.commit('CLEAR_CURRENT_SHOW');
        const currentPath = router.currentRoute.path;
        if (currentPath.startsWith('/show-config') || currentPath.startsWith('/live')) {
          router.push('/');
        }
      }
    },
    async GET_RBAC_ROLES(context) {
      const response = await fetch(makeURL('/api/v1/rbac/roles'));
      if (response.ok) {
        const rbac = await response.json();
        await context.commit('UPDATE_RBAC_ROLES', rbac.roles);
      } else {
        log.error('Unable to fetch RBAC roles');
      }
    },
  },
  getters: {
    DEBUG_MODE_ENABLED(state) {
      if (Object.keys(state.settings).includes('debug_mode')) {
        return state.settings.debug_mode;
      }
      return false;
    },
    SETTINGS(state) {
      return state.settings;
    },
    RAW_SETTINGS(state) {
      return state.rawSettings;
    },
    RBAC_ROLES(state) {
      return state.rbacRoles;
    },
  },
};
