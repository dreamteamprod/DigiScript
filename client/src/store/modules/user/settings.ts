import Vue from 'vue';
import log from 'loglevel';
import type { Module } from 'vuex';

import { makeURL } from '@/js/utils';
import type { RootState } from '@/types/store';
import type { StageDirectionStyle } from '@/types/api/script';
import type { CueColourOverride } from '@/types/api/user';

interface SettingsState {
  userSettings: Record<string, unknown>;
  stageDirectionStyleOverrides: StageDirectionStyle[];
  cueColourOverrides: CueColourOverride[];
}

const VueToast = Vue as typeof Vue & {
  $toast: {
    success: (m: string) => void;
    error: (m: string) => void;
  };
};

const module: Module<SettingsState, RootState> = {
  state: {
    userSettings: {},
    stageDirectionStyleOverrides: [],
    cueColourOverrides: [],
  },
  mutations: {
    SET_USER_SETTINGS(state: SettingsState, settings: Record<string, unknown>) {
      state.userSettings = settings;
    },
    SET_STAGE_DIRECTION_STYLE_OVERRIDES(state: SettingsState, overrides: StageDirectionStyle[]) {
      state.stageDirectionStyleOverrides = overrides;
    },
    SET_CUE_COLOUR_OVERRIDES(state: SettingsState, overrides: CueColourOverride[]) {
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
    async UPDATE_TABLE_PAGE_SIZE(
      context,
      { tableKey, value }: { tableKey: string; value: number }
    ) {
      const current =
        (context.state.userSettings as { table_page_sizes?: Record<string, number> })
          .table_page_sizes ?? {};
      await fetch(makeURL('/api/v1/user/settings'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ table_page_sizes: { ...current, [tableKey]: value } }),
      });
    },
    async UPDATE_SETTINGS(context, payload) {
      context.commit('UPDATE_SETTINGS', payload);
      await context.dispatch('SETTINGS_CHANGED');
    },
    async GET_STAGE_DIRECTION_STYLE_OVERRIDES(context) {
      const response = await fetch(
        `${makeURL('/api/v1/user/settings/stage_direction_overrides')}`,
        { method: 'GET', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_STAGE_DIRECTION_STYLE_OVERRIDES', respJson.overrides);
      } else {
        log.error('Unable to load stage direction style overrides');
      }
    },
    async ADD_STAGE_DIRECTION_STYLE_OVERRIDE(context, style: StageDirectionStyle) {
      const response = await fetch(
        `${makeURL('/api/v1/user/settings/stage_direction_overrides')}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(style),
        }
      );
      if (response.ok) {
        context.dispatch('GET_STAGE_DIRECTION_STYLE_OVERRIDES');
        VueToast.$toast.success('Added new stage direction style override!');
      } else {
        log.error('Unable to add new stage direction style override');
        VueToast.$toast.error('Unable to add new stage direction style override');
      }
    },
    async DELETE_STAGE_DIRECTION_STYLE_OVERRIDE(context, styleId: number) {
      const response = await fetch(
        `${makeURL('/api/v1/user/settings/stage_direction_overrides')}?id=${styleId}`,
        { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        context.dispatch('GET_STAGE_DIRECTION_STYLE_OVERRIDES');
        VueToast.$toast.success('Deleted stage direction style override!');
      } else {
        log.error('Unable to delete stage direction style override');
        VueToast.$toast.error('Unable to delete stage direction style override');
      }
    },
    async UPDATE_STAGE_DIRECTION_STYLE_OVERRIDE(context, style: StageDirectionStyle) {
      const response = await fetch(
        `${makeURL('/api/v1/user/settings/stage_direction_overrides')}`,
        {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(style),
        }
      );
      if (response.ok) {
        context.dispatch('GET_STAGE_DIRECTION_STYLE_OVERRIDES');
        VueToast.$toast.success('Updated stage direction style override!');
      } else {
        log.error('Unable to edit stage direction style override');
        VueToast.$toast.error('Unable to edit stage direction style override');
      }
    },
    async GET_CUE_COLOUR_OVERRIDES(context) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/cue_colour_overrides')}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_CUE_COLOUR_OVERRIDES', respJson.overrides);
      } else {
        log.error('Unable to load cue colour overrides');
      }
    },
    async ADD_CUE_COLOUR_OVERRIDE(context, override: CueColourOverride) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/cue_colour_overrides')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(override),
      });
      if (response.ok) {
        context.dispatch('GET_CUE_COLOUR_OVERRIDES');
        VueToast.$toast.success('Added new cue colour override!');
      } else {
        log.error('Unable to add new cue colour override');
        VueToast.$toast.error('Unable to add new cue colour override');
      }
    },
    async DELETE_CUE_COLOUR_OVERRIDE(context, overrideId: number) {
      const response = await fetch(
        `${makeURL(`/api/v1/user/settings/cue_colour_overrides?id=${overrideId}`)}`,
        { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        context.dispatch('GET_CUE_COLOUR_OVERRIDES');
        VueToast.$toast.success('Deleted cue colour override!');
      } else {
        log.error('Unable to delete cue colour override');
        VueToast.$toast.error('Unable to delete cue colour override');
      }
    },
    async UPDATE_CUE_COLOUR_OVERRIDE(context, override: CueColourOverride) {
      const response = await fetch(`${makeURL('/api/v1/user/settings/cue_colour_overrides')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(override),
      });
      if (response.ok) {
        context.dispatch('GET_CUE_COLOUR_OVERRIDES');
        VueToast.$toast.success('Updated cue colour override!');
      } else {
        log.error('Unable to edit cue colour override');
        VueToast.$toast.error('Unable to edit cue colour override');
      }
    },
  },
  getters: {
    USER_SETTINGS(state: SettingsState) {
      return state.userSettings;
    },
    STAGE_DIRECTION_STYLE_OVERRIDES(state: SettingsState) {
      return state.stageDirectionStyleOverrides;
    },
    CUE_COLOUR_OVERRIDES(state: SettingsState) {
      return state.cueColourOverrides;
    },
  },
};

export default module;
