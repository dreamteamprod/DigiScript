import Vue from 'vue';

import { makeURL } from '@/js/utils';

export default {
  state: {
    editStatus: {
      editors: [],
      cutters: [],
      hasDraft: false,
    },
    cutMode: false,
  },
  mutations: {
    SET_EDIT_STATUS(state, editStatus) {
      state.editStatus = editStatus;
    },
    SET_CUT_MODE(state, cutMode) {
      state.cutMode = cutMode;
    },
  },
  actions: {
    REQUEST_EDIT_FAILURE(context, message) {
      Vue.$toast.error(message?.DATA?.reason || 'Unable to edit script');
      context.dispatch('GET_SCRIPT_CONFIG_STATUS');
      context.commit('SET_CUT_MODE', false);
    },
    async GET_SCRIPT_CONFIG_STATUS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/script/config')}`);
      if (response.ok) {
        const status = await response.json();
        context.commit('SET_EDIT_STATUS', status);
      }
    },
  },
  getters: {
    EDITORS(state) {
      return state.editStatus.editors;
    },
    CUTTERS(state) {
      return state.editStatus.cutters;
    },
    HAS_DRAFT(state) {
      return state.editStatus.hasDraft;
    },
    CAN_REQUEST_EDIT(state, getters, rootState, rootGetters) {
      if (rootGetters.CURRENT_SHOW_SESSION) return false;
      return state.editStatus.cutters.length === 0;
    },
    CAN_REQUEST_CUTS(state, getters, rootState, rootGetters) {
      if (rootGetters.CURRENT_SHOW_SESSION) return false;
      return (
        state.editStatus.editors.length === 0 &&
        state.editStatus.cutters.length === 0 &&
        !state.editStatus.hasDraft
      );
    },
    IS_CURRENT_EDITOR: (state, getters, rootState, rootGetters) => {
      const uuid = rootGetters.INTERNAL_UUID;
      return state.editStatus.editors.some((e) => e.internal_id === uuid);
    },
    IS_CURRENT_CUTTER: (state, getters, rootState, rootGetters) => {
      const uuid = rootGetters.INTERNAL_UUID;
      return state.editStatus.cutters.some((c) => c.internal_id === uuid);
    },
    IS_CUT_MODE(state) {
      return state.cutMode;
    },
  },
};
