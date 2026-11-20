import { defineStore } from 'pinia';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
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

export const useStageStore = defineStore('stage', {
  state: () => ({
    crewList: [] as Crew[],
    crewAssignments: [] as CrewAssignment[],
    sceneryTypes: [] as SceneryType[],
    sceneryList: [] as Scenery[],
    sceneryAllocations: [] as SceneryAllocation[],
    propTypes: [] as PropType[],
    propsList: [] as Props[],
    propsAllocations: [] as PropsAllocation[],
  }),

  getters: {
    crewById: (state) => (id: number | null) =>
      id == null ? null : (state.crewList.find((c) => c.id === id) ?? null),

    sceneryById: (state) => (id: number | null) =>
      id == null ? null : (state.sceneryList.find((s) => s.id === id) ?? null),

    sceneryTypeById: (state) => (id: number | null) =>
      id == null ? null : (state.sceneryTypes.find((t) => t.id === id) ?? null),

    propById: (state) => (id: number | null) =>
      id == null ? null : (state.propsList.find((p) => p.id === id) ?? null),

    propTypeById: (state) => (id: number | null) =>
      id == null ? null : (state.propTypes.find((t) => t.id === id) ?? null),

    sceneryTypesDict: (state) =>
      Object.fromEntries(state.sceneryTypes.map((t) => [t.id, t])) as Record<number, SceneryType>,

    propTypesDict: (state) =>
      Object.fromEntries(state.propTypes.map((t) => [t.id, t])) as Record<number, PropType>,

    propsAllocationsByItem: (state) => {
      const result: Record<number, PropsAllocation[]> = {};
      state.propsAllocations.forEach((alloc) => {
        if (!result[alloc.props_id]) result[alloc.props_id] = [];
        result[alloc.props_id].push(alloc);
      });
      return result;
    },

    sceneryAllocationsByItem: (state) => {
      const result: Record<number, SceneryAllocation[]> = {};
      state.sceneryAllocations.forEach((alloc) => {
        if (!result[alloc.scenery_id]) result[alloc.scenery_id] = [];
        result[alloc.scenery_id].push(alloc);
      });
      return result;
    },

    crewAssignmentsByProp: (state) => {
      const result: Record<number, CrewAssignment[]> = {};
      state.crewAssignments.forEach((a) => {
        if (a.prop_id != null) {
          if (!result[a.prop_id]) result[a.prop_id] = [];
          result[a.prop_id].push(a);
        }
      });
      return result;
    },

    crewAssignmentsByScenery: (state) => {
      const result: Record<number, CrewAssignment[]> = {};
      state.crewAssignments.forEach((a) => {
        if (a.scenery_id != null) {
          if (!result[a.scenery_id]) result[a.scenery_id] = [];
          result[a.scenery_id].push(a);
        }
      });
      return result;
    },

    crewAssignmentsByCrew: (state) => {
      const result: Record<number, CrewAssignment[]> = {};
      state.crewAssignments.forEach((a) => {
        if (!result[a.crew_id]) result[a.crew_id] = [];
        result[a.crew_id].push(a);
      });
      return result;
    },

    crewAssignmentsByScene: (state) => {
      const result: Record<number, CrewAssignment[]> = {};
      state.crewAssignments.forEach((a) => {
        if (!result[a.scene_id]) result[a.scene_id] = [];
        result[a.scene_id].push(a);
      });
      return result;
    },
  },

  actions: {
    async getCrewList() {
      const response = await fetch(makeURL('/api/v1/show/stage/crew'));
      if (response.ok) {
        const data = await response.json();
        this.crewList = data.crew;
      } else {
        log.error('Unable to get crew list');
      }
    },

    async addCrewMember(crewMember: Partial<Crew>) {
      const response = await fetch(makeURL('/api/v1/show/stage/crew'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ firstName: crewMember.first_name, lastName: crewMember.last_name }),
      });
      if (response.ok) {
        await this.getCrewList();
        toast.success('Added new crew member!');
      } else {
        log.error('Unable to add new crew member');
        toast.error('Unable to add new crew member');
      }
    },

    async updateCrewMember(crewMember: Partial<Crew>) {
      const response = await fetch(makeURL('/api/v1/show/stage/crew'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: crewMember.id,
          firstName: crewMember.first_name,
          lastName: crewMember.last_name,
        }),
      });
      if (response.ok) {
        await this.getCrewList();
        toast.success('Updated crew member!');
      } else {
        log.error('Unable to edit crew member');
        toast.error('Unable to edit crew member');
      }
    },

    async deleteCrewMember(crewId: number) {
      const params = new URLSearchParams({ id: String(crewId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew')}?${params}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await this.getCrewList();
        toast.success('Deleted crew member!');
      } else {
        log.error('Unable to delete crew member');
        toast.error('Unable to delete crew member');
      }
    },

    async getSceneryTypes() {
      const response = await fetch(makeURL('/api/v1/show/stage/scenery/types'));
      if (response.ok) {
        const data = await response.json();
        this.sceneryTypes = data.scenery_types;
      } else {
        log.error('Unable to get scenery types');
      }
    },

    async addSceneryType(sceneryType: Partial<SceneryType>) {
      const response = await fetch(makeURL('/api/v1/show/stage/scenery/types'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sceneryType),
      });
      if (response.ok) {
        await this.getSceneryTypes();
        toast.success('Added new scenery type!');
      } else {
        log.error('Unable to add new scenery type');
        toast.error('Unable to add new scenery type');
      }
    },

    async updateSceneryType(sceneryType: Partial<SceneryType>) {
      const response = await fetch(makeURL('/api/v1/show/stage/scenery/types'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sceneryType),
      });
      if (response.ok) {
        await this.getSceneryTypes();
        toast.success('Updated scenery type!');
      } else {
        log.error('Unable to edit scenery type');
        toast.error('Unable to edit scenery type');
      }
    },

    async deleteSceneryType(sceneryTypeId: number) {
      const params = new URLSearchParams({ id: String(sceneryTypeId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery/types')}?${params}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await Promise.all([this.getSceneryTypes(), this.getSceneryList()]);
        toast.success('Deleted scenery type!');
      } else {
        log.error('Unable to delete scenery type');
        toast.error('Unable to delete scenery type');
      }
    },

    async getSceneryList() {
      const response = await fetch(makeURL('/api/v1/show/stage/scenery'));
      if (response.ok) {
        const data = await response.json();
        this.sceneryList = data.scenery;
      } else {
        log.error('Unable to get scenery list');
      }
    },

    async addScenery(scenery: Partial<Scenery>) {
      const response = await fetch(makeURL('/api/v1/show/stage/scenery'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenery),
      });
      if (response.ok) {
        await this.getSceneryList();
        toast.success('Added new scenery!');
      } else {
        log.error('Unable to add new scenery');
        toast.error('Unable to add new scenery');
      }
    },

    async updateScenery(scenery: Partial<Scenery>) {
      const response = await fetch(makeURL('/api/v1/show/stage/scenery'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scenery),
      });
      if (response.ok) {
        await this.getSceneryList();
        toast.success('Updated scenery!');
      } else {
        log.error('Unable to edit scenery');
        toast.error('Unable to edit scenery');
      }
    },

    async deleteScenery(sceneryId: number) {
      const params = new URLSearchParams({ id: String(sceneryId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/scenery')}?${params}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await this.getSceneryList();
        toast.success('Deleted scenery!');
      } else {
        log.error('Unable to delete scenery');
        toast.error('Unable to delete scenery');
      }
    },

    async getPropTypes() {
      const response = await fetch(makeURL('/api/v1/show/stage/props/types'));
      if (response.ok) {
        const data = await response.json();
        this.propTypes = data.prop_types;
      } else {
        log.error('Unable to get prop types');
      }
    },

    async addPropType(propType: Partial<PropType>) {
      const response = await fetch(makeURL('/api/v1/show/stage/props/types'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(propType),
      });
      if (response.ok) {
        await this.getPropTypes();
        toast.success('Added new prop type!');
      } else {
        log.error('Unable to add new prop type');
        toast.error('Unable to add new prop type');
      }
    },

    async updatePropType(propType: Partial<PropType>) {
      const response = await fetch(makeURL('/api/v1/show/stage/props/types'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(propType),
      });
      if (response.ok) {
        await this.getPropTypes();
        toast.success('Updated prop type!');
      } else {
        log.error('Unable to edit prop type');
        toast.error('Unable to edit prop type');
      }
    },

    async deletePropType(propTypeId: number) {
      const params = new URLSearchParams({ id: String(propTypeId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/types')}?${params}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await Promise.all([this.getPropTypes(), this.getPropsList()]);
        toast.success('Deleted prop type!');
      } else {
        log.error('Unable to delete prop type');
        toast.error('Unable to delete prop type');
      }
    },

    async getPropsList() {
      const response = await fetch(makeURL('/api/v1/show/stage/props'));
      if (response.ok) {
        const data = await response.json();
        this.propsList = data.props;
      } else {
        log.error('Unable to get props list');
      }
    },

    async addProp(prop: Partial<Props>) {
      const response = await fetch(makeURL('/api/v1/show/stage/props'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prop),
      });
      if (response.ok) {
        await this.getPropsList();
        toast.success('Added new prop!');
      } else {
        log.error('Unable to add new prop');
        toast.error('Unable to add new prop');
      }
    },

    async updateProp(prop: Partial<Props>) {
      const response = await fetch(makeURL('/api/v1/show/stage/props'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prop),
      });
      if (response.ok) {
        await this.getPropsList();
        toast.success('Updated prop!');
      } else {
        log.error('Unable to edit prop');
        toast.error('Unable to edit prop');
      }
    },

    async deleteProp(propId: number) {
      const params = new URLSearchParams({ id: String(propId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/props')}?${params}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await this.getPropsList();
        toast.success('Deleted prop!');
      } else {
        log.error('Unable to delete prop');
        toast.error('Unable to delete prop');
      }
    },

    async getPropsAllocations() {
      const response = await fetch(makeURL('/api/v1/show/stage/props/allocations'));
      if (response.ok) {
        const data = await response.json();
        this.propsAllocations = data.allocations;
      } else {
        log.error('Unable to get props allocations');
      }
    },

    async addPropsAllocation(allocation: Partial<PropsAllocation>) {
      const response = await fetch(makeURL('/api/v1/show/stage/props/allocations'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(allocation),
      });
      if (response.ok) {
        await this.getPropsAllocations();
        toast.success('Added prop allocation!');
      } else {
        log.error('Unable to add prop allocation');
        toast.error('Unable to add prop allocation');
      }
    },

    async deletePropsAllocation(allocationId: number) {
      const params = new URLSearchParams({ id: String(allocationId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/props/allocations')}?${params}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await this.getPropsAllocations();
        toast.success('Deleted prop allocation!');
      } else {
        log.error('Unable to delete prop allocation');
        toast.error('Unable to delete prop allocation');
      }
    },

    async getSceneryAllocations() {
      const response = await fetch(makeURL('/api/v1/show/stage/scenery/allocations'));
      if (response.ok) {
        const data = await response.json();
        this.sceneryAllocations = data.allocations;
      } else {
        log.error('Unable to get scenery allocations');
      }
    },

    async addSceneryAllocation(allocation: Partial<SceneryAllocation>) {
      const response = await fetch(makeURL('/api/v1/show/stage/scenery/allocations'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(allocation),
      });
      if (response.ok) {
        await this.getSceneryAllocations();
        toast.success('Added scenery allocation!');
      } else {
        log.error('Unable to add scenery allocation');
        toast.error('Unable to add scenery allocation');
      }
    },

    async deleteSceneryAllocation(allocationId: number) {
      const params = new URLSearchParams({ id: String(allocationId) });
      const response = await fetch(
        `${makeURL('/api/v1/show/stage/scenery/allocations')}?${params}`,
        { method: 'DELETE' }
      );
      if (response.ok) {
        await this.getSceneryAllocations();
        toast.success('Deleted scenery allocation!');
      } else {
        log.error('Unable to delete scenery allocation');
        toast.error('Unable to delete scenery allocation');
      }
    },

    async getCrewAssignments() {
      const response = await fetch(makeURL('/api/v1/show/stage/crew/assignments'));
      if (response.ok) {
        const data = await response.json();
        this.crewAssignments = data.assignments;
      } else {
        log.error('Unable to get crew assignments');
      }
    },

    async addCrewAssignment(assignment: Partial<CrewAssignment>): Promise<boolean> {
      const response = await fetch(makeURL('/api/v1/show/stage/crew/assignments'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(assignment),
      });
      if (response.ok) {
        await this.getCrewAssignments();
        toast.success('Added crew assignment!');
        return true;
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg =
          (errorData as { message?: string }).message ?? 'Unable to add crew assignment';
        log.error(errorMsg);
        toast.error(errorMsg);
        return false;
      }
    },

    async deleteCrewAssignment(assignmentId: number) {
      const params = new URLSearchParams({ id: String(assignmentId) });
      const response = await fetch(`${makeURL('/api/v1/show/stage/crew/assignments')}?${params}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        await this.getCrewAssignments();
        toast.success('Deleted crew assignment!');
      } else {
        const errorData = await response.json().catch(() => ({}));
        const errorMsg =
          (errorData as { message?: string }).message ?? 'Unable to delete crew assignment';
        log.error(errorMsg);
        toast.error(errorMsg);
      }
    },
  },
});
