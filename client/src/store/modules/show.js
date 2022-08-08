import Vue from 'vue';

export default {
  state: {
    castList: [],
  },
  mutations: {
    SET_CAST_LIST(state, castList) {
      state.castList = castList;
    },
  },
  actions: {
    async GET_CAST_LIST(context) {
      const response = await fetch(`${utils.makeURL('/api/v1/show/cast')}?${$.param({
        show_id: context.rootState.currentShow.id,
      })}`);
      if (response.ok) {
        const cast = await response.json();
        context.commit('SET_CAST_LIST', cast.cast);
      } else {
        console.error('Unable to get cast list');
      }
    },
    async ADD_CAST_MEMBER(context, castMember) {
      const response = await fetch(`${utils.makeURL('/api/v1/show/cast')}?${$.param({
        show_id: context.rootState.currentShow.id,
      })}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(castMember),
      });
      if (response.ok) {
        context.dispatch('GET_CAST_LIST');
        Vue.$toast.success('Added new cast member!');
      } else {
        console.error('Unable to add new cast member');
        Vue.$toast.error('Unable to add new cast member');
      }
    },
    async DELETE_CAST_MEMBER(context, castID) {
      const response = await fetch(`${utils.makeURL('/api/v1/show/cast')}?${$.param({
        show_id: context.rootState.currentShow.id,
      })}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: castID }),
      });
      if (response.ok) {
        context.dispatch('GET_CAST_LIST');
        Vue.$toast.success('Deleted cast member!');
      } else {
        console.error('Unable to delete cast member');
        Vue.$toast.error('Unable to delete cast member');
      }
    },
    async UPDATE_CAST_MEMBER(context, castMember) {
      const response = await fetch(`${utils.makeURL('/api/v1/show/cast')}?${$.param({
        show_id: context.rootState.currentShow.id,
      })}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(castMember),
      });
      if (response.ok) {
        context.dispatch('GET_CAST_LIST');
        Vue.$toast.success('Updated cast member!');
      } else {
        console.error('Unable to edit cast member');
        Vue.$toast.error('Unable to edit cast member');
      }
    },
  },
  getters: {
    CAST_LIST(state) {
      return state.castList;
    },
  },
};
