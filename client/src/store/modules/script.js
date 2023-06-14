import Vue from 'vue';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
  state: {
    currentRevision: null,
    revisions: [],
    script: {},
    cues: {},
    cuts: [],
  },
  mutations: {
    SET_REVISIONS(state, revisions) {
      state.revisions = revisions;
    },
    SET_CURRENT_REVISION(state, currentRevision) {
      state.currentRevision = currentRevision;
    },
    SET_SCRIPT_PAGE(state, { pageNumber, page }) {
      Vue.set(state.script, pageNumber, page);
    },
    SET_CUES(state, cues) {
      state.cues = cues;
    },
    SET_CUTS(state, cuts) {
      state.cuts = cuts;
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
        log.error('Unable to get script revisions');
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
        log.error('Unable to add new script revision');
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
        log.error('Unable to delete script revision');
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
        log.error('Unable to load script revision');
        Vue.$toast.error('Unable to load script revision');
      }
    },
    async SCRIPT_REVISION_CHANGED(context) {
      await context.dispatch('GET_SCRIPT_REVISIONS');
      /* eslint-disable no-await-in-loop, no-restricted-syntax */
      for (const page of Object.keys(context.state.script)) {
        await context.dispatch('LOAD_SCRIPT_PAGE', page);
        await context.dispatch('ADD_BLANK_PAGE', page);
      }
      await context.dispatch('LOAD_CUES');
      await context.dispatch('GET_CUTS');
      /* eslint-enable no-await-in-loop, no-restricted-syntax */
    },
    async LOAD_SCRIPT_PAGE(context, page) {
      const searchParams = new URLSearchParams({
        page,
      });
      const response = await fetch(`${makeURL('/api/v1/show/script')}?${searchParams}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_SCRIPT_PAGE', {
          pageNumber: respJson.page,
          page: respJson.lines,
        });
      } else {
        log.error('Unable to load script page');
      }
    },
    async LOAD_CUES(context) {
      const response = await fetch(`${makeURL('/api/v1/show/cues')}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_CUES', respJson.cues);
      } else {
        log.error('Unable to load cues');
      }
    },
    async ADD_NEW_CUE(context, cue) {
      const response = await fetch(`${makeURL('/api/v1/show/cues')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(cue),
      });
      if (response.ok) {
        context.dispatch('LOAD_CUES');
        Vue.$toast.success('Added new cue!');
      } else {
        log.error('Unable to add new cue');
        Vue.$toast.error('Unable to add new cue');
      }
    },
    async EDIT_CUE(context, cue) {
      const response = await fetch(`${makeURL('/api/v1/show/cues')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(cue),
      });
      if (response.ok) {
        context.dispatch('LOAD_CUES');
        Vue.$toast.success('Edited cue!');
      } else {
        log.error('Unable to edit cue');
        Vue.$toast.error('Unable to edit cue');
      }
    },
    async DELETE_CUE(context, cue) {
      const response = await fetch(`${makeURL('/api/v1/show/cues')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(cue),
      });
      if (response.ok) {
        context.dispatch('LOAD_CUES');
        Vue.$toast.success('Deleted cue!');
      } else {
        log.error('Unable to delete cue');
        Vue.$toast.error('Unable to delete cue');
      }
    },
    async GET_CUTS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/script/cuts')}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_CUTS', respJson.cuts);
      } else {
        log.error('Unable to load script cuts');
      }
    },
    async SAVE_SCRIPT_CUTS(context, cuts) {
      const response = await fetch(`${makeURL('/api/v1/show/script/cuts')}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          cuts,
        }),
      });
      if (response.ok) {
        await context.dispatch('GET_CUTS');
        Vue.$toast.success('Saved script cuts!');
      } else {
        log.error('Unable to save script cuts');
        Vue.$toast.error('Unable to save script cuts');
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
    GET_SCRIPT_PAGE: (state) => (page) => {
      const pageStr = page.toString();
      if (Object.keys(state.script).includes(pageStr)) {
        return state.script[pageStr];
      }
      return [];
    },
    SCRIPT_CUES(state) {
      return state.cues;
    },
    SCRIPT_CUTS(state) {
      return state.cuts;
    },
  },
};
