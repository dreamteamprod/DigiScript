import Vue from 'vue';

import { makeURL } from '@/js/utils';

export default {
  state: {
    currentRevision: null,
    revisions: [],
  },
  mutations: {
    SET_REVISIONS(state, revisions) {
      state.revisions = revisions;
    },
    SET_CURRENT_REVISION(state, currentRevision) {
      state.currentRevision = currentRevision;
    },
  },
  actions: {
    async GET_SCRIPT_REVISIONS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/script/revisions')}`);
      if (response.ok) {
        const revisions = await response.json();
        context.commit('SET_REVISIONS', revisions.revisions);
        context.commit('SET_CURRENT_REVISION', revisions.current_revision);
      } else {
        console.error('Unable to get script revisions');
      }
    },
    async ADD_SCRIPT_REVISION(context, scriptRevision) {
      const response = await fetch(`${makeURL('/api/v1/show/script/revisions')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(scriptRevision),
      });
      if (response.ok) {
        context.dispatch('GET_SCRIPT_REVISIONS');
        Vue.$toast.success('Added new script revision!');
      } else {
        console.error('Unable to add new script revision');
        Vue.$toast.error('Unable to add new script revision');
      }
    },
    async DELETE_SCRIPT_REVISION(context, revisionID) {
      const response = await fetch(`${makeURL('/api/v1/show/script/revisions')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          rev_id: revisionID,
        }),
      });
      if (response.ok) {
        context.dispatch('GET_SCRIPT_REVISIONS');
        Vue.$toast.success('Deleted script revision!');
      } else {
        console.error('Unable to delete script revision');
        Vue.$toast.error('Unable to delete script revision');
      }
    },
    async LOAD_SCRIPT_REVISION(context, revisionID) {
      const response = await fetch(`${makeURL('/api/v1/show/script/revisions/current')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          new_rev_id: revisionID,
        }),
      });
      if (response.ok) {
        context.dispatch('GET_SCRIPT_REVISIONS');
        Vue.$toast.success('Loaded script revision!');
      } else {
        console.error('Unable to load script revision');
        Vue.$toast.error('Unable to load script revision');
      }
    },
  },
  getters: {
    SCRIPT_REVISIONS(state) {
      return state.revisions;
    },
    CURRENT_REVISION(state) {
      return state.currentRevision;
    },
  },
};
