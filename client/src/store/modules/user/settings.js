import Vue from 'vue';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
  state: {
    userSettings: {},
    stageDirectionStyleOverrides: [],
    cueColourOverrides: [],
  },
  mutations: {
    SET_USER_SETTINGS(state, settings) {
      state.userSettings = settings;
    },
    SET_STAGE_DIRECTION_STYLE_OVERRIDES(state, overrides) {
      state.stageDirectionStyleOverrides = overrides;
    },
    SET_CUE_COLOUR_OVERRIDES(state, overrides) {
      state.cueColourOverrides = overrides;
    },
  },
  actions: {
    async GET_USER_SETTINGS(context) {
      const response = await fetch(makeURL('/api/v1/user/settings'));
      if (response.ok) {
        const settings = await response.json();
        await context.commit('SET_USER_SETTINGS', settings);
      } else {
        log.error('Unable to fetch user settings');
      }
    },
    async UPDATE_SETTINGS(context, payload) {
      context.commit('UPDATE_SETTINGS', payload);
      await context.dispatch('SETTINGS_CHANGED');
    },
    async GET_STAGE_DIRECTION_STYLE_OVERRIDES(context) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/stage_direction_overrides')}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_STAGE_DIRECTION_STYLE_OVERRIDES', respJson.overrides);
      } else {
        log.error('Unable to load stage direction style overrides');
      }
    },
    async ADD_STAGE_DIRECTION_STYLE_OVERRIDE(context, style) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/stage_direction_overrides')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(style),
      });
      if (response.ok) {
        context.dispatch('GET_STAGE_DIRECTION_STYLE_OVERRIDES');
        Vue.$toast.success('Added new stage direction style override!');
      } else {
        log.error('Unable to add new stage direction style override');
        Vue.$toast.error('Unable to add new stage direction style override');
      }
    },
    async DELETE_STAGE_DIRECTION_STYLE_OVERRIDE(context, styleId) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/stage_direction_overrides')}?id=${styleId}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        context.dispatch('GET_STAGE_DIRECTION_STYLE_OVERRIDES');
        Vue.$toast.success('Deleted stage direction style override!');
      } else {
        log.error('Unable to delete stage direction style override');
        Vue.$toast.error('Unable to delete stage direction style override');
      }
    },
    async UPDATE_STAGE_DIRECTION_STYLE_OVERRIDE(context, style) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/stage_direction_overrides')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(style),
      });
      if (response.ok) {
        context.dispatch('GET_STAGE_DIRECTION_STYLE_OVERRIDES');
        Vue.$toast.success('Updated stage direction style override!');
      } else {
        log.error('Unable to edit stage direction style override');
        Vue.$toast.error('Unable to edit stage direction style override');
      }
    },
    async GET_CUE_COLOUR_OVERRIDES(context) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/cue_colour_overrides')}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_CUE_COLOUR_OVERRIDES', respJson.overrides);
      } else {
        log.error('Unable to load cue colour overrides');
      }
    },
    async ADD_CUE_COLOUR_OVERRIDE(context, override) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/cue_colour_overrides')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(override),
      });
      if (response.ok) {
        context.dispatch('GET_CUE_COLOUR_OVERRIDES');
        Vue.$toast.success('Added new cue colour override!');
      } else {
        log.error('Unable to add new cue colour override');
        Vue.$toast.error('Unable to add new cue colour override');
      }
    },
    async DELETE_CUE_COLOUR_OVERRIDE(context, overrideId) {
      const response = await fetch(`${makeURL(`/api/v1/user/settings/cue_colour_overrides?id=${overrideId}`)}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        context.dispatch('GET_CUE_COLOUR_OVERRIDES');
        Vue.$toast.success('Deleted cue colour override!');
      } else {
        log.error('Unable to delete cue colour override');
        Vue.$toast.error('Unable to delete cue colour override');
      }
    },
    async UPDATE_CUE_COLOUR_OVERRIDE(context, override) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/cue_colour_overrides')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(override),
      });
      if (response.ok) {
        context.dispatch('GET_CUE_COLOUR_OVERRIDES');
        Vue.$toast.success('Updated cue colour override!');
      } else {
        log.error('Unable to edit cue colour override');
        Vue.$toast.error('Unable to edit cue colour override');
      }
    },
  },
  getters: {
    USER_SETTINGS(state) {
      return state.userSettings;
    },
    STAGE_DIRECTION_STYLE_OVERRIDES(state) {
      return state.stageDirectionStyleOverrides;
    },
    CUE_COLOUR_OVERRIDES(state) {
      return state.cueColourOverrides;
    },
  },
};
