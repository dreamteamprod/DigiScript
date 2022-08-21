import { makeURL } from '@/js/utils';

export default {
  state: {
    revisions: [],
  },
  mutations: {
    SET_REVISIONS(state, revisions) {
      state.revisions = revisions;
    },
  },
  actions: {
    async GET_SCRIPT_REVISIONS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/script/revisions')}`);
      if (response.ok) {
        const revisions = await response.json();
        context.commit('SET_REVISIONS', revisions.revisions);
      } else {
        console.error('Unable to get script revisions');
      }
    },
  },
  getters: {
    SCRIPT_REVISIONS(state) {
      return state.revisions;
    },
  },
};
