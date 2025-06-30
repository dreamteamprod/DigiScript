import Vue from 'vue';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
  state: {
    crewList: [],
    sceneryList: [],
    propsList: [],
  },
  mutations: {
    SET_CREW_LIST(state, crewList) {
      state.crewList = crewList;
    },
    SET_SCENERY_LIST(state, sceneryList) {
      state.sceneryList = sceneryList;
    },
    SET_PROPS_LIST(state, propsList) {
      state.propsList = propsList;
    },
  },
  actions: {
    async GET_CREW_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew')}`);
      if (response.ok) {
        const crew = await response.json();
        context.commit('SET_CREW_LIST', crew.crew);
      } else {
        log.error('Unable to get crew list');
      }
    },
    async ADD_CREW_MEMBER(context, crewMember) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(crewMember),
      });
      if (response.ok) {
        context.dispatch('GET_CREW_LIST');
        Vue.$toast.success('Added new crew member!');
      } else {
        log.error('Unable to add new crew member');
        Vue.$toast.error('Unable to add new crew member');
      }
    },
    async DELETE_CREW_MEMBER(context, crewId) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: crewId }),
      });
      if (response.ok) {
        context.dispatch('GET_CREW_LIST');
        Vue.$toast.success('Deleted crew member!');
      } else {
        log.error('Unable to delete crew member');
        Vue.$toast.error('Unable to delete crew member');
      }
    },
    async UPDATE_CREW_MEMBER(context, crewMember) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(crewMember),
      });
      if (response.ok) {
        context.dispatch('GET_CREW_LIST');
        Vue.$toast.success('Updated crew member!');
      } else {
        log.error('Unable to edit crew member');
        Vue.$toast.error('Unable to edit crew member');
      }
    },
    async GET_SCENERY_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery')}`);
      if (response.ok) {
        const scenery = await response.json();
        context.commit('SET_SCENERY_LIST', scenery.scenery);
      } else {
        log.error('Unable to get scenery list');
      }
    },
    async ADD_SCENERY_MEMBER(context, sceneryMember) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sceneryMember),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_LIST');
        Vue.$toast.success('Added new scenery member!');
      } else {
        log.error('Unable to add new scenery member');
        Vue.$toast.error('Unable to add new scenery member');
      }
    },
    async DELETE_SCENERY_MEMBER(context, sceneryId) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: sceneryId }),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_LIST');
        Vue.$toast.success('Deleted scenery member!');
      } else {
        log.error('Unable to delete scenery member');
        Vue.$toast.error('Unable to delete scenery member');
      }
    },
    async UPDATE_SCENERY_MEMBER(context, sceneryMember) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sceneryMember),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_LIST');
        Vue.$toast.success('Updated scenery member!');
      } else {
        log.error('Unable to edit scenery member');
        Vue.$toast.error('Unable to edit scenery member');
      }
    },
    async GET_PROPS_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props')}`);
      if (response.ok) {
        const props = await response.json();
        context.commit('SET_PROPS_LIST', props.props);
      } else {
        log.error('Unable to get props list');
      }
    },
    async ADD_PROPS_MEMBER(context, propsMember) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(propsMember),
      });
      if (response.ok) {
        context.dispatch('GET_PROPS_LIST');
        Vue.$toast.success('Added new props member!');
      } else {
        log.error('Unable to add new props member');
        Vue.$toast.error('Unable to add new props member');
      }
    },
    async DELETE_PROPS_MEMBER(context, propsId) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: propsId }),
      });
      if (response.ok) {
        context.dispatch('GET_PROPS_LIST');
        Vue.$toast.success('Deleted props member!');
      } else {
        log.error('Unable to delete props member');
        Vue.$toast.error('Unable to delete props member');
      }
    },
    async UPDATE_PROPS_MEMBER(context, propsMember) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(propsMember),
      });
      if (response.ok) {
        context.dispatch('GET_PROPS_LIST');
        Vue.$toast.success('Updated props member!');
      } else {
        log.error('Unable to edit props member');
        Vue.$toast.error('Unable to edit props member');
      }
    },
  },
  getters: {
    CREW_LIST(state) {
      return state.crewList;
    },
    SCENERY_LIST(state) {
      return state.sceneryList;
    },
    PROPS_LIST(state) {
      return state.propsList;
    },
  },
};
