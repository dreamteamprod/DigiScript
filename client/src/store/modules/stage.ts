import Vue from 'vue';
import log from 'loglevel';
import type { Module } from 'vuex';

import { makeURL } from '@/js/utils';
import type { RootState } from '@/types/store';
import type {
  Crew,
  CrewAssignment,
  SceneryType,
  Scenery,
  SceneryAllocation,
  PropType,
  Props,
  PropsAllocation,
} from '@/types/api/stage';

interface StageState {
  crewList: Crew[];
  crewAssignments: CrewAssignment[];
  sceneryTypes: SceneryType[];
  sceneryList: Scenery[];
  sceneryAllocations: SceneryAllocation[];
  propTypes: PropType[];
  propsList: Props[];
  propsAllocations: PropsAllocation[];
}

const VueToast = Vue as typeof Vue & {
  $toast: { success: (m: string) => void; error: (m: string) => void };
};

const module: Module<StageState, RootState> = {
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
    SET_CREW_LIST(state: StageState, crewList: Crew[]) {
      state.crewList = crewList;
    },
    SET_CREW_ASSIGNMENTS(state: StageState, assignments: CrewAssignment[]) {
      state.crewAssignments = assignments;
    },
    SET_SCENERY_TYPES(state: StageState, sceneryTypes: SceneryType[]) {
      state.sceneryTypes = sceneryTypes;
    },
    SET_SCENERY_LIST(state: StageState, sceneryList: Scenery[]) {
      state.sceneryList = sceneryList;
    },
    SET_PROP_TYPES(state: StageState, propTypes: PropType[]) {
      state.propTypes = propTypes;
    },
    SET_PROPS_LIST(state: StageState, propsList: Props[]) {
      state.propsList = propsList;
    },
    SET_PROPS_ALLOCATIONS(state: StageState, allocations: PropsAllocation[]) {
      state.propsAllocations = allocations;
    },
    SET_SCENERY_ALLOCATIONS(state: StageState, allocations: SceneryAllocation[]) {
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
    async ADD_CREW_MEMBER(context, crewMember: Partial<Crew>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(crewMember),
      });
      if (response.ok) {
        context.dispatch('GET_CREW_LIST');
        VueToast.$toast.success('Added new crew member!');
      } else {
        log.error('Unable to add new crew member');
        VueToast.$toast.error('Unable to add new crew member');
      }
    },
    async DELETE_CREW_MEMBER(context, crewId: number) {
      const searchParams = new URLSearchParams({ id: String(crewId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_CREW_LIST');
        VueToast.$toast.success('Deleted crew member!');
      } else {
        log.error('Unable to delete crew member');
        VueToast.$toast.error('Unable to delete crew member');
      }
    },
    async UPDATE_CREW_MEMBER(context, crewMember: Partial<Crew>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(crewMember),
      });
      if (response.ok) {
        context.dispatch('GET_CREW_LIST');
        VueToast.$toast.success('Updated crew member!');
      } else {
        log.error('Unable to edit crew member');
        VueToast.$toast.error('Unable to edit crew member');
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
    async ADD_SCENERY_TYPE(context, sceneryType: Partial<SceneryType>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery/types')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sceneryType),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_TYPES');
        VueToast.$toast.success('Added new scenery type!');
      } else {
        log.error('Unable to add new scenery type');
        VueToast.$toast.error('Unable to add new scenery type');
      }
    },
    async DELETE_SCENERY_TYPE(context, sceneryTypeId: number) {
      const searchParams = new URLSearchParams({ id: String(sceneryTypeId) });
      const response = await fetch(
        `${makeURL('/api/v1/show/stage/scenery/types')}?${searchParams}`,
        { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        context.dispatch('GET_SCENERY_TYPES');
        context.dispatch('GET_SCENERY_LIST');
        VueToast.$toast.success('Deleted scenery type!');
      } else {
        log.error('Unable to delete scenery type');
        VueToast.$toast.error('Unable to delete scenery type');
      }
    },
    async UPDATE_SCENERY_TYPE(context, sceneryType: Partial<SceneryType>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery/types')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sceneryType),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_TYPES');
        VueToast.$toast.success('Updated scenery type!');
      } else {
        log.error('Unable to edit scenery type');
        VueToast.$toast.error('Unable to edit scenery type');
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
    async ADD_SCENERY(context, sceneryMember: Partial<Scenery>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sceneryMember),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_LIST');
        VueToast.$toast.success('Added new scenery member!');
      } else {
        log.error('Unable to add new scenery member');
        VueToast.$toast.error('Unable to add new scenery member');
      }
    },
    async DELETE_SCENERY(context, sceneryId: number) {
      const searchParams = new URLSearchParams({ id: String(sceneryId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_LIST');
        VueToast.$toast.success('Deleted scenery member!');
      } else {
        log.error('Unable to delete scenery member');
        VueToast.$toast.error('Unable to delete scenery member');
      }
    },
    async UPDATE_SCENERY(context, sceneryMember: Partial<Scenery>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sceneryMember),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_LIST');
        VueToast.$toast.success('Updated scenery member!');
      } else {
        log.error('Unable to edit scenery member');
        VueToast.$toast.error('Unable to edit scenery member');
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
    async ADD_PROP_TYPE(context, propType: Partial<PropType>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/types')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(propType),
      });
      if (response.ok) {
        context.dispatch('GET_PROP_TYPES');
        VueToast.$toast.success('Added new prop type!');
      } else {
        log.error('Unable to add new prop type');
        VueToast.$toast.error('Unable to add new prop type');
      }
    },
    async DELETE_PROP_TYPE(context, propTypeId: number) {
      const searchParams = new URLSearchParams({ id: String(propTypeId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/types')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_PROP_TYPES');
        context.dispatch('GET_PROPS_LIST');
        VueToast.$toast.success('Deleted prop type!');
      } else {
        log.error('Unable to delete prop type');
        VueToast.$toast.error('Unable to delete prop type');
      }
    },
    async UPDATE_PROP_TYPE(context, propType: Partial<PropType>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/types')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(propType),
      });
      if (response.ok) {
        context.dispatch('GET_PROP_TYPES');
        VueToast.$toast.success('Updated prop type!');
      } else {
        log.error('Unable to edit prop type');
        VueToast.$toast.error('Unable to edit prop type');
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
    async ADD_PROP(context, propsMember: Partial<Props>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(propsMember),
      });
      if (response.ok) {
        context.dispatch('GET_PROPS_LIST');
        VueToast.$toast.success('Added new props member!');
      } else {
        log.error('Unable to add new props member');
        VueToast.$toast.error('Unable to add new props member');
      }
    },
    async DELETE_PROP(context, propsId: number) {
      const searchParams = new URLSearchParams({ id: String(propsId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/props')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_PROPS_LIST');
        VueToast.$toast.success('Deleted props member!');
      } else {
        log.error('Unable to delete props member');
        VueToast.$toast.error('Unable to delete props member');
      }
    },
    async UPDATE_PROP(context, propsMember: Partial<Props>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(propsMember),
      });
      if (response.ok) {
        context.dispatch('GET_PROPS_LIST');
        VueToast.$toast.success('Updated props member!');
      } else {
        log.error('Unable to edit props member');
        VueToast.$toast.error('Unable to edit props member');
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
    async ADD_PROPS_ALLOCATION(context, allocation: Partial<PropsAllocation>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/allocations')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(allocation),
      });
      if (response.ok) {
        context.dispatch('GET_PROPS_ALLOCATIONS');
        VueToast.$toast.success('Added prop allocation!');
      } else {
        log.error('Unable to add prop allocation');
        VueToast.$toast.error('Unable to add prop allocation');
      }
    },
    async DELETE_PROPS_ALLOCATION(context, allocationId: number) {
      const searchParams = new URLSearchParams({ id: String(allocationId) });
      const response = await fetch(
        `${makeURL('/api/v1/show/stage/props/allocations')}?${searchParams}`,
        { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        context.dispatch('GET_PROPS_ALLOCATIONS');
        VueToast.$toast.success('Deleted prop allocation!');
      } else {
        log.error('Unable to delete prop allocation');
        VueToast.$toast.error('Unable to delete prop allocation');
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
    async ADD_SCENERY_ALLOCATION(context, allocation: Partial<SceneryAllocation>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery/allocations')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(allocation),
      });
      if (response.ok) {
        context.dispatch('GET_SCENERY_ALLOCATIONS');
        VueToast.$toast.success('Added scenery allocation!');
      } else {
        log.error('Unable to add scenery allocation');
        VueToast.$toast.error('Unable to add scenery allocation');
      }
    },
    async DELETE_SCENERY_ALLOCATION(context, allocationId: number) {
      const searchParams = new URLSearchParams({ id: String(allocationId) });
      const response = await fetch(
        `${makeURL('/api/v1/show/stage/scenery/allocations')}?${searchParams}`,
        { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        context.dispatch('GET_SCENERY_ALLOCATIONS');
        VueToast.$toast.success('Deleted scenery allocation!');
      } else {
        log.error('Unable to delete scenery allocation');
        VueToast.$toast.error('Unable to delete scenery allocation');
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
    async ADD_CREW_ASSIGNMENT(context, assignment: Partial<CrewAssignment>) {
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew/assignments')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(assignment),
      });
      if (response.ok) {
        context.dispatch('GET_CREW_ASSIGNMENTS');
        VueToast.$toast.success('Added crew assignment!');
        return { success: true };
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg = errorData.message || 'Unable to add crew assignment';
        log.error(errorMsg);
        VueToast.$toast.error(errorMsg);
        return { success: false, error: errorMsg };
      }
    },
    async DELETE_CREW_ASSIGNMENT(context, assignmentId: number) {
      const searchParams = new URLSearchParams({ id: String(assignmentId) });
      const response = await fetch(
        `${makeURL('/api/v1/show/stage/crew/assignments')}?${searchParams}`,
        { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        context.dispatch('GET_CREW_ASSIGNMENTS');
        VueToast.$toast.success('Deleted crew assignment!');
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg = errorData.message || 'Unable to delete crew assignment';
        log.error(errorMsg);
        VueToast.$toast.error(errorMsg);
      }
    },
  },
  getters: {
    CREW_LIST(state: StageState) {
      return state.crewList;
    },
    PROP_BY_ID: (state: StageState) => (propId: number | null) => {
      if (propId == null) return null;
      return state.propsList.find((p) => p.id === propId) || null;
    },
    SCENERY_BY_ID: (state: StageState) => (sceneryId: number | null) => {
      if (sceneryId == null) return null;
      return state.sceneryList.find((s) => s.id === sceneryId) || null;
    },
    PROPS_ALLOCATIONS_BY_ITEM(state: StageState) {
      const result: Record<number, PropsAllocation[]> = {};
      state.propsAllocations.forEach((alloc) => {
        if (!result[alloc.props_id]) {
          result[alloc.props_id] = [];
        }
        result[alloc.props_id].push(alloc);
      });
      return result;
    },
    SCENERY_ALLOCATIONS_BY_ITEM(state: StageState) {
      const result: Record<number, SceneryAllocation[]> = {};
      state.sceneryAllocations.forEach((alloc) => {
        if (!result[alloc.scenery_id]) {
          result[alloc.scenery_id] = [];
        }
        result[alloc.scenery_id].push(alloc);
      });
      return result;
    },
    SCENERY_TYPES(state: StageState) {
      return state.sceneryTypes;
    },
    SCENERY_TYPES_DICT(state: StageState) {
      return Object.fromEntries(
        state.sceneryTypes.map((sceneryType) => [sceneryType.id, sceneryType])
      );
    },
    SCENERY_TYPE_BY_ID: (_state: StageState, getters) => (sceneryTypeId: number | null) => {
      if (sceneryTypeId == null) return null;
      const sceneryTypeStr = sceneryTypeId.toString();
      if (Object.keys(getters.SCENERY_TYPES_DICT).includes(sceneryTypeStr)) {
        return getters.SCENERY_TYPES_DICT[sceneryTypeStr];
      }
      return null;
    },
    SCENERY_LIST(state: StageState) {
      return state.sceneryList;
    },
    PROP_TYPES(state: StageState) {
      return state.propTypes;
    },
    PROP_TYPES_DICT(state: StageState) {
      return Object.fromEntries(state.propTypes.map((propType) => [propType.id, propType]));
    },
    PROP_TYPE_BY_ID: (_state: StageState, getters) => (propTypeId: number | null) => {
      if (propTypeId == null) return null;
      const propTypeStr = propTypeId.toString();
      if (Object.keys(getters.PROP_TYPES_DICT).includes(propTypeStr)) {
        return getters.PROP_TYPES_DICT[propTypeStr];
      }
      return null;
    },
    PROPS_LIST(state: StageState) {
      return state.propsList;
    },
    PROPS_ALLOCATIONS(state: StageState) {
      return state.propsAllocations;
    },
    SCENERY_ALLOCATIONS(state: StageState) {
      return state.sceneryAllocations;
    },
    CREW_ASSIGNMENTS(state: StageState) {
      return state.crewAssignments;
    },
    CREW_MEMBER_BY_ID: (state: StageState) => (crewId: number | null) => {
      if (crewId == null) return null;
      return state.crewList.find((c) => c.id === crewId) || null;
    },
    CREW_ASSIGNMENTS_BY_PROP(state: StageState) {
      const result: Record<number, CrewAssignment[]> = {};
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
    CREW_ASSIGNMENTS_BY_SCENERY(state: StageState) {
      const result: Record<number, CrewAssignment[]> = {};
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
    CREW_ASSIGNMENTS_BY_CREW(state: StageState) {
      const result: Record<number, CrewAssignment[]> = {};
      state.crewAssignments.forEach((assignment) => {
        if (!result[assignment.crew_id]) {
          result[assignment.crew_id] = [];
        }
        result[assignment.crew_id].push(assignment);
      });
      return result;
    },
    CREW_ASSIGNMENTS_BY_SCENE(state: StageState) {
      const result: Record<number, CrewAssignment[]> = {};
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

export default module;
