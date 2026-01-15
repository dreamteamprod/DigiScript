import Vue from 'vue';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
  state: {
    crewList: [],
    sceneryTypes: [],
    sceneryList: [],
    propTypes: [],
    propsList: [],
  },
  mutations: {
    SET_CREW_LIST(state, crewList) {
      state.crewList = crewList;
    },
    SET_SCENERY_TYPES(state, sceneryTypes) {
      state.sceneryTypes = sceneryTypes;
    },
    SET_SCENERY_LIST(state, sceneryList) {
      state.sceneryList = sceneryList;
    },
    SET_PROP_TYPES(state, propTypes) {
      state.propTypes = propTypes;
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
    async GET_SCENERY_TYPES(context) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery/types')}`);
      if (response.ok) {
        const scenery = await response.json();
        context.commit('SET_SCENERY_TYPES', scenery.scenery_types);
      } else {
        log.error('Unable to get scenery types list');
      }
    },
    async ADD_SCENERY_TYPE(context, sceneryType) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery/types')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sceneryType),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_TYPES');
        Vue.$toast.success('Added new scenery type!');
      } else {
        log.error('Unable to add new scenery type');
        Vue.$toast.error('Unable to add new scenery type');
      }
    },
    async DELETE_SCENERY_TYPE(context, sceneryTypeId) {
      const searchParams = new URLSearchParams({
        id: sceneryTypeId,
      });
      const response = await fetch(
        `${makeURL('/api/v1/show/stage/scenery/types')}?${searchParams}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      if (response.ok) {
        context.dispatch('GET_SCENERY_TYPES');
        context.dispatch('GET_SCENERY_LIST');
        Vue.$toast.success('Deleted scenery type!');
      } else {
        log.error('Unable to delete scenery type');
        Vue.$toast.error('Unable to delete scenery type');
      }
    },
    async UPDATE_SCENERY_TYPE(context, sceneryType) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery/types')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(sceneryType),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_TYPES');
        Vue.$toast.success('Updated scenery type!');
      } else {
        log.error('Unable to edit scenery type');
        Vue.$toast.error('Unable to edit scenery type');
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
    async ADD_SCENERY(context, sceneryMember) {
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
    async DELETE_SCENERY(context, sceneryId) {
      const searchParams = new URLSearchParams({
        id: sceneryId,
      });
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery')}?${searchParams}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_LIST');
        Vue.$toast.success('Deleted scenery member!');
      } else {
        log.error('Unable to delete scenery member');
        Vue.$toast.error('Unable to delete scenery member');
      }
    },
    async UPDATE_SCENERY(context, sceneryMember) {
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
    async GET_PROP_TYPES(context) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/types')}`);
      if (response.ok) {
        const props = await response.json();
        context.commit('SET_PROP_TYPES', props.prop_types);
      } else {
        log.error('Unable to get prop types list');
      }
    },
    async ADD_PROP_TYPE(context, propType) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/types')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(propType),
      });
      if (response.ok) {
        context.dispatch('GET_PROP_TYPES');
        Vue.$toast.success('Added new prop type!');
      } else {
        log.error('Unable to add new prop type');
        Vue.$toast.error('Unable to add new prop type');
      }
    },
    async DELETE_PROP_TYPE(context, propTypeId) {
      const searchParams = new URLSearchParams({
        id: propTypeId,
      });
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/types')}?${searchParams}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        context.dispatch('GET_PROP_TYPES');
        context.dispatch('GET_PROPS_LIST');
        Vue.$toast.success('Deleted prop type!');
      } else {
        log.error('Unable to delete prop type');
        Vue.$toast.error('Unable to delete prop type');
      }
    },
    async UPDATE_PROP_TYPE(context, propType) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/types')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(propType),
      });
      if (response.ok) {
        context.dispatch('GET_PROP_TYPES');
        Vue.$toast.success('Updated prop type!');
      } else {
        log.error('Unable to edit prop type');
        Vue.$toast.error('Unable to edit prop type');
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
    async ADD_PROP(context, propsMember) {
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
    async DELETE_PROP(context, propsId) {
      const searchParams = new URLSearchParams({
        id: propsId,
      });
      const response = await fetch(`${makeURL('/api/v1/show/stage/props')}?${searchParams}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        context.dispatch('GET_PROPS_LIST');
        Vue.$toast.success('Deleted props member!');
      } else {
        log.error('Unable to delete props member');
        Vue.$toast.error('Unable to delete props member');
      }
    },
    async UPDATE_PROP(context, propsMember) {
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
    SCENERY_TYPES(state) {
      return state.sceneryTypes;
    },
    SCENERY_TYPES_DICT(state) {
      return Object.fromEntries(
        state.sceneryTypes.map((sceneryType) => [sceneryType.id, sceneryType])
      );
    },
    SCENERY_TYPE_BY_ID: (state, getters) => (sceneryTypeId) => {
      if (sceneryTypeId == null) {
        return null;
      }
      const sceneryTypeStr = sceneryTypeId.toString();
      if (Object.keys(getters.SCENERY_TYPES_DICT).includes(sceneryTypeStr)) {
        return getters.SCENERY_TYPES_DICT[sceneryTypeStr];
      }
      return null;
    },
    SCENERY_LIST(state) {
      return state.sceneryList;
    },
    PROP_TYPES(state) {
      return state.propTypes;
    },
    PROP_TYPES_DICT(state) {
      return Object.fromEntries(state.propTypes.map((propType) => [propType.id, propType]));
    },
    PROP_TYPE_BY_ID: (state, getters) => (propTypeId) => {
      if (propTypeId == null) {
        return null;
      }
      const propTypeStr = propTypeId.toString();
      if (Object.keys(getters.PROP_TYPES_DICT).includes(propTypeStr)) {
        return getters.PROP_TYPES_DICT[propTypeStr];
      }
      return null;
    },
    PROPS_LIST(state) {
      return state.propsList;
    },
  },
};
