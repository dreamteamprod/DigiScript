import log from 'loglevel';
import type { Module } from 'vuex';

import router from '@/router';
import { makeURL } from '@/js/utils';
import type { RootState } from '@/types/store';
import type { Show } from '@/types/api/show';
import type { SystemSettings } from '@/types/api/settings';

interface SystemState {
  settings: SystemSettings | Record<string, never>;
  availableShows: Show[];
  rawSettings: Record<string, unknown>;
  rbacRoles: Array<{ key: string; value: number }>;
  settingsCategories: Record<string, unknown>;
}

const module: Module<SystemState, RootState> = {
  state: {
    settings: {},
    availableShows: [],
    rawSettings: {},
    rbacRoles: [],
    settingsCategories: {},
  },
  mutations: {
    UPDATE_SETTINGS(state: SystemState, settings: SystemSettings) {
      state.settings = settings;
    },
    UPDATE_SHOWS(state: SystemState, shows: Show[]) {
      state.availableShows = shows;
    },
    UPDATE_RAW_SETTINGS(state: SystemState, settings: Record<string, unknown>) {
      state.rawSettings = settings;
    },
    UPDATE_RBAC_ROLES(state: SystemState, rbac: Array<{ key: string; value: number }>) {
      state.rbacRoles = rbac;
    },
    UPDATE_SETTINGS_CATEGORIES(state: SystemState, categories: Record<string, unknown>) {
      state.settingsCategories = categories;
    },
  },
  actions: {
    async GET_AVAILABLE_SHOWS(context) {
      const response = await fetch(`${makeURL('/api/v1/shows')}`);
      if (response.ok) {
        const shows = await response.json();
        context.commit('UPDATE_SHOWS', shows.shows);
      } else {
        log.error('Unable to get available shows');
      }
    },
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
    async UPDATE_SETTINGS(context, payload: SystemSettings) {
      context.commit('UPDATE_SETTINGS', payload);
      await context.dispatch('SETTINGS_CHANGED');
    },
    async SETTINGS_CHANGED(context) {
      await context.dispatch('GET_RAW_SETTINGS');

      if (context.state.settings.current_show) {
        const currShow = context.state.settings.current_show;
        if (!context.rootState.currentShow || context.rootState.currentShow.id !== currShow) {
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
    async GET_SETTINGS_CATEGORIES(context) {
      const response = await fetch(makeURL('/api/v1/settings/categories'));
      if (response.ok) {
        const categories = await response.json();
        await context.commit('UPDATE_SETTINGS_CATEGORIES', categories.categories);
      } else {
        log.error('Unable to fetch settings categories');
      }
    },
  },
  getters: {
    AVAILABLE_SHOWS(state: SystemState) {
      return state.availableShows;
    },
    SETTINGS(state: SystemState) {
      return state.settings;
    },
    RAW_SETTINGS(state: SystemState) {
      return state.rawSettings;
    },
    RBAC_ROLES(state: SystemState) {
      return state.rbacRoles;
    },
    SETTINGS_CATEGORIES(state: SystemState) {
      return state.settingsCategories;
    },
  },
};

export default module;
