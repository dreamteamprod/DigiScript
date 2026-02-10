import Vue from 'vue';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
  state: {
    crewList: [],
    crewAssignments: [],
    sceneryTypes: [],
    sceneryList: [],
    sceneryAllocations: [],
    propTypes: [],
    propsList: [],
    propsAllocations: [],
  },
  mutations: {
    SET_CREW_LIST(state, crewList) {
      state.crewList = crewList;
    },
    SET_CREW_ASSIGNMENTS(state, assignments) {
      state.crewAssignments = assignments;
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
    SET_PROPS_ALLOCATIONS(state, allocations) {
      state.propsAllocations = allocations;
    },
    SET_SCENERY_ALLOCATIONS(state, allocations) {
      state.sceneryAllocations = allocations;
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
      const searchParams = new URLSearchParams({ id: crewId });
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew')}?${searchParams}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
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
    async GET_PROPS_ALLOCATIONS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/allocations')}`);
      if (response.ok) {
        const data = await response.json();
        context.commit('SET_PROPS_ALLOCATIONS', data.allocations);
      } else {
        log.error('Unable to get props allocations');
      }
    },
    async ADD_PROPS_ALLOCATION(context, allocation) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/allocations')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(allocation),
      });
      if (response.ok) {
        context.dispatch('GET_PROPS_ALLOCATIONS');
        Vue.$toast.success('Added prop allocation!');
      } else {
        log.error('Unable to add prop allocation');
        Vue.$toast.error('Unable to add prop allocation');
      }
    },
    async DELETE_PROPS_ALLOCATION(context, allocationId) {
      const searchParams = new URLSearchParams({
        id: allocationId,
      });
      const response = await fetch(
        `${makeURL('/api/v1/show/stage/props/allocations')}?${searchParams}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      if (response.ok) {
        context.dispatch('GET_PROPS_ALLOCATIONS');
        Vue.$toast.success('Deleted prop allocation!');
      } else {
        log.error('Unable to delete prop allocation');
        Vue.$toast.error('Unable to delete prop allocation');
      }
    },
    async GET_SCENERY_ALLOCATIONS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery/allocations')}`);
      if (response.ok) {
        const data = await response.json();
        context.commit('SET_SCENERY_ALLOCATIONS', data.allocations);
      } else {
        log.error('Unable to get scenery allocations');
      }
    },
    async ADD_SCENERY_ALLOCATION(context, allocation) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery/allocations')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(allocation),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_ALLOCATIONS');
        Vue.$toast.success('Added scenery allocation!');
      } else {
        log.error('Unable to add scenery allocation');
        Vue.$toast.error('Unable to add scenery allocation');
      }
    },
    async DELETE_SCENERY_ALLOCATION(context, allocationId) {
      const searchParams = new URLSearchParams({
        id: allocationId,
      });
      const response = await fetch(
        `${makeURL('/api/v1/show/stage/scenery/allocations')}?${searchParams}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      if (response.ok) {
        context.dispatch('GET_SCENERY_ALLOCATIONS');
        Vue.$toast.success('Deleted scenery allocation!');
      } else {
        log.error('Unable to delete scenery allocation');
        Vue.$toast.error('Unable to delete scenery allocation');
      }
    },
    async GET_CREW_ASSIGNMENTS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew/assignments')}`);
      if (response.ok) {
        const data = await response.json();
        context.commit('SET_CREW_ASSIGNMENTS', data.assignments);
      } else {
        log.error('Unable to get crew assignments');
      }
    },
    async ADD_CREW_ASSIGNMENT(context, assignment) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew/assignments')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(assignment),
      });
      if (response.ok) {
        context.dispatch('GET_CREW_ASSIGNMENTS');
        Vue.$toast.success('Added crew assignment!');
        return { success: true };
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg = errorData.error || 'Unable to add crew assignment';
        log.error(errorMsg);
        Vue.$toast.error(errorMsg);
        return { success: false, error: errorMsg };
      }
    },
    async DELETE_CREW_ASSIGNMENT(context, assignmentId) {
      const searchParams = new URLSearchParams({ id: assignmentId });
      const response = await fetch(
        `${makeURL('/api/v1/show/stage/crew/assignments')}?${searchParams}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
      if (response.ok) {
        context.dispatch('GET_CREW_ASSIGNMENTS');
        Vue.$toast.success('Deleted crew assignment!');
      } else {
        log.error('Unable to delete crew assignment');
        Vue.$toast.error('Unable to delete crew assignment');
      }
    },
  },
  getters: {
    CREW_LIST(state) {
      return state.crewList;
    },
    PROP_BY_ID: (state) => (propId) => {
      if (propId == null) return null;
      return state.propsList.find((p) => p.id === propId) || null;
    },
    SCENERY_BY_ID: (state) => (sceneryId) => {
      if (sceneryId == null) return null;
      return state.sceneryList.find((s) => s.id === sceneryId) || null;
    },
    PROPS_ALLOCATIONS_BY_ITEM(state) {
      const result = {};
      state.propsAllocations.forEach((alloc) => {
        if (!result[alloc.props_id]) {
          result[alloc.props_id] = [];
        }
        result[alloc.props_id].push(alloc);
      });
      return result;
    },
    SCENERY_ALLOCATIONS_BY_ITEM(state) {
      const result = {};
      state.sceneryAllocations.forEach((alloc) => {
        if (!result[alloc.scenery_id]) {
          result[alloc.scenery_id] = [];
        }
        result[alloc.scenery_id].push(alloc);
      });
      return result;
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
    PROPS_ALLOCATIONS(state) {
      return state.propsAllocations;
    },
    SCENERY_ALLOCATIONS(state) {
      return state.sceneryAllocations;
    },
    CREW_ASSIGNMENTS(state) {
      return state.crewAssignments;
    },
    CREW_MEMBER_BY_ID: (state) => (crewId) => {
      if (crewId == null) return null;
      return state.crewList.find((c) => c.id === crewId) || null;
    },
    CREW_ASSIGNMENTS_BY_PROP(state) {
      const result = {};
      state.crewAssignments.forEach((assignment) => {
        if (assignment.prop_id != null) {
          if (!result[assignment.prop_id]) {
            result[assignment.prop_id] = [];
          }
          result[assignment.prop_id].push(assignment);
        }
      });
      return result;
    },
    CREW_ASSIGNMENTS_BY_SCENERY(state) {
      const result = {};
      state.crewAssignments.forEach((assignment) => {
        if (assignment.scenery_id != null) {
          if (!result[assignment.scenery_id]) {
            result[assignment.scenery_id] = [];
          }
          result[assignment.scenery_id].push(assignment);
        }
      });
      return result;
    },
    CREW_ASSIGNMENTS_BY_CREW(state) {
      const result = {};
      state.crewAssignments.forEach((assignment) => {
        if (!result[assignment.crew_id]) {
          result[assignment.crew_id] = [];
        }
        result[assignment.crew_id].push(assignment);
      });
      return result;
    },
    CREW_ASSIGNMENTS_BY_SCENE(state) {
      const result = {};
      state.crewAssignments.forEach((assignment) => {
        if (!result[assignment.scene_id]) {
          result[assignment.scene_id] = [];
        }
        result[assignment.scene_id].push(assignment);
      });
      return result;
    },
  },
};
