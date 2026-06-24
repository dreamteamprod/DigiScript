import Vue from 'vue';
import log from 'loglevel';
import type { Module } from 'vuex';

import { makeURL } from '@/js/utils';
import type { RootState } from '@/types/store';
import type {
  ScriptLine,
  ScriptRevision,
  StageDirectionStyle,
  ScriptCut,
  CompiledScript,
} from '@/types/api/script';
import type { Cue, CueGroup } from '@/types/api/cues';

interface ScriptState {
  currentRevision: number | null;
  revisions: ScriptRevision[];
  script: Record<string, ScriptLine[]>;
  cues: Record<string, Cue[]>;
  cueGroups: CueGroup[];
  cuts: ScriptCut[];
  stageDirectionStyles: StageDirectionStyle[];
  compiledScripts: CompiledScript[];
}

const VueToast = Vue as typeof Vue & {
  $toast: { success: (m: string) => void; error: (m: string) => void };
};

const module: Module<ScriptState, RootState> = {
  state: {
    currentRevision: null,
    revisions: [],
    script: {},
    cues: {},
    cueGroups: [],
    cuts: [],
    stageDirectionStyles: [],
    compiledScripts: [],
  },
  mutations: {
    SET_REVISIONS(state: ScriptState, revisions: ScriptRevision[]) {
      state.revisions = revisions;
    },
    SET_CURRENT_REVISION(state: ScriptState, currentRevision: number | null) {
      state.currentRevision = currentRevision;
    },
    SET_SCRIPT_PAGE(
      state: ScriptState,
      { pageNumber, page }: { pageNumber: string; page: ScriptLine[] }
    ) {
      Vue.set(state.script, pageNumber, page);
    },
    SET_CUES(state: ScriptState, cues: Record<string, Cue[]>) {
      state.cues = cues;
    },
    SET_CUE_GROUPS(state: ScriptState, cueGroups: CueGroup[]) {
      state.cueGroups = cueGroups;
    },
    SET_CUTS(state: ScriptState, cuts: ScriptCut[]) {
      state.cuts = cuts;
    },
    SET_STAGE_DIRECTION_STYLES(state: ScriptState, styles: StageDirectionStyle[]) {
      state.stageDirectionStyles = styles;
    },
    SET_COMPILED_SCRIPTS(state: ScriptState, compiledScripts: CompiledScript[]) {
      state.compiledScripts = compiledScripts;
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
    async ADD_SCRIPT_REVISION(
      context,
      scriptRevision: {
        description: string;
        parent_revision_id?: number | null;
        set_as_current?: boolean | null;
      }
    ) {
      const payload: Record<string, unknown> = {
        description: scriptRevision.description,
      };

      if (scriptRevision.parent_revision_id != null) {
        payload.parent_revision_id = scriptRevision.parent_revision_id;
      }

      if (scriptRevision.set_as_current != null) {
        payload.set_as_current = scriptRevision.set_as_current;
      }

      const response = await fetch(`${makeURL('/api/v1/show/script/revisions')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        context.dispatch('GET_SCRIPT_REVISIONS');
        VueToast.$toast.success('Added new script revision!');
      } else {
        log.error('Unable to add new script revision');
        VueToast.$toast.error('Unable to add new script revision');
      }
    },
    async DELETE_SCRIPT_REVISION(context, revisionID: number) {
      const searchParams = new URLSearchParams({ rev_id: String(revisionID) });
      const response = await fetch(`${makeURL('/api/v1/show/script/revisions')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_SCRIPT_REVISIONS');
        VueToast.$toast.success('Deleted script revision!');
      } else {
        log.error('Unable to delete script revision');
        VueToast.$toast.error('Unable to delete script revision');
      }
    },
    async LOAD_SCRIPT_REVISION(context, revisionID: number) {
      const response = await fetch(`${makeURL('/api/v1/show/script/revisions/current')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_rev_id: revisionID }),
      });
      if (response.ok) {
        context.dispatch('GET_SCRIPT_REVISIONS');
        VueToast.$toast.success('Loaded script revision!');
      } else {
        log.error('Unable to load script revision');
        VueToast.$toast.error('Unable to load script revision');
      }
    },
    async SCRIPT_REVISION_CHANGED(context) {
      await context.dispatch('GET_SCRIPT_REVISIONS');

      for (const page of Object.keys(context.state.script)) {
        await context.dispatch('LOAD_SCRIPT_PAGE', page);
        await context.dispatch('ADD_BLANK_PAGE', page);
      }
      await context.dispatch('LOAD_CUES');
      await context.dispatch('GET_CUTS');
    },
    async SCRIPT_PAGE_CHANGED(context, msg: { DATA: { page: number } }) {
      const page = String(msg.DATA.page);
      if (Object.hasOwn(context.state.script, page)) {
        await context.dispatch('LOAD_SCRIPT_PAGE', page);
        await context.dispatch('ADD_BLANK_PAGE', page);
      }
    },
    async LOAD_SCRIPT_PAGE(context, page: string | number) {
      const searchParams = new URLSearchParams({ page: String(page) });
      const response = await fetch(`${makeURL('/api/v1/show/script')}?${searchParams}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_SCRIPT_PAGE', { pageNumber: respJson.page, page: respJson.lines });
      } else {
        log.error('Unable to load script page');
      }
    },
    async LOAD_CUES(context) {
      const response = await fetch(`${makeURL('/api/v1/show/cues')}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_CUES', respJson.cues);
        context.commit('SET_CUE_GROUPS', respJson.cue_groups ?? []);
      } else {
        log.error('Unable to load cues');
      }
    },
    async ADD_NEW_CUE(context, cue: Partial<Cue>) {
      const response = await fetch(`${makeURL('/api/v1/show/cues')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cue),
      });
      if (response.ok) {
        context.dispatch('LOAD_CUES');
        VueToast.$toast.success('Added new cue!');
      } else {
        log.error('Unable to add new cue');
        VueToast.$toast.error('Unable to add new cue');
      }
    },
    async EDIT_CUE(context, cue: Partial<Cue>) {
      const response = await fetch(`${makeURL('/api/v1/show/cues')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cue),
      });
      if (response.ok) {
        context.dispatch('LOAD_CUES');
        VueToast.$toast.success('Edited cue!');
      } else {
        log.error('Unable to edit cue');
        VueToast.$toast.error('Unable to edit cue');
      }
    },
    async DELETE_CUE(context, cue: { cueId: number; lineId: number }) {
      const searchParams = new URLSearchParams({
        cueId: String(cue.cueId),
        lineId: String(cue.lineId),
      });
      const response = await fetch(`${makeURL('/api/v1/show/cues')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('LOAD_CUES');
        VueToast.$toast.success('Deleted cue!');
      } else {
        log.error('Unable to delete cue');
        VueToast.$toast.error('Unable to delete cue');
      }
    },
    async ADD_CUE_GROUP(
      context,
      payload: {
        cueTypeId: number;
        labelOverride?: string;
        lineId: number;
        cues: { ident: string; sortOrder: number }[];
      }
    ) {
      const response = await fetch(`${makeURL('/api/v1/show/cues/groups')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        context.dispatch('LOAD_CUES');
        VueToast.$toast.success('Added cue group!');
      } else {
        log.error('Unable to add cue group');
        VueToast.$toast.error('Unable to add cue group');
      }
    },
    async EDIT_CUE_GROUP(
      context,
      payload: {
        groupId: number;
        labelOverride?: string;
        lineId: number;
        cues: { id?: number; ident: string; sortOrder: number }[];
      }
    ) {
      const response = await fetch(`${makeURL('/api/v1/show/cues/groups')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (response.ok) {
        context.dispatch('LOAD_CUES');
        VueToast.$toast.success('Edited cue group!');
      } else {
        log.error('Unable to edit cue group');
        VueToast.$toast.error('Unable to edit cue group');
      }
    },
    async DELETE_CUE_GROUP(context, payload: { groupId: number; lineId: number }) {
      const params = new URLSearchParams({
        groupId: String(payload.groupId),
        lineId: String(payload.lineId),
      });
      const response = await fetch(`${makeURL('/api/v1/show/cues/groups')}?${params}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('LOAD_CUES');
        VueToast.$toast.success('Deleted cue group!');
      } else {
        log.error('Unable to delete cue group');
        VueToast.$toast.error('Unable to delete cue group');
      }
    },
    async SEARCH_CUES(
      _context,
      { identifier, cueTypeId }: { identifier: string; cueTypeId: number }
    ) {
      const params = new URLSearchParams();
      params.append('identifier', identifier);
      params.append('cue_type_id', String(cueTypeId));

      const response = await fetch(`${makeURL('/api/v1/show/cues/search')}?${params}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        return response.json();
      }
      log.error('Unable to search for cue');
      throw new Error('Cue search failed');
    },
    async GET_CUTS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/script/cuts')}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_CUTS', respJson.cuts);
      } else {
        log.error('Unable to load script cuts');
      }
    },
    async SAVE_SCRIPT_CUTS(context, cuts: ScriptCut[]) {
      const response = await fetch(`${makeURL('/api/v1/show/script/cuts')}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cuts }),
      });
      if (response.ok) {
        await context.dispatch('GET_CUTS');
        VueToast.$toast.success('Saved script cuts!');
      } else {
        log.error('Unable to save script cuts');
        VueToast.$toast.error('Unable to save script cuts');
      }
    },
    async GET_STAGE_DIRECTION_STYLES(context) {
      const response = await fetch(`${makeURL('/api/v1/show/script/stage_direction_styles')}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_STAGE_DIRECTION_STYLES', respJson.styles);
      } else {
        log.error('Unable to load stage direction styles');
      }
    },
    async ADD_STAGE_DIRECTION_STYLE(context, style: Partial<StageDirectionStyle>) {
      const response = await fetch(`${makeURL('/api/v1/show/script/stage_direction_styles')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(style),
      });
      if (response.ok) {
        context.dispatch('GET_STAGE_DIRECTION_STYLES');
        VueToast.$toast.success('Added new stage direction style!');
      } else {
        log.error('Unable to add new stage direction style');
        VueToast.$toast.error('Unable to add new stage direction style');
      }
    },
    async DELETE_STAGE_DIRECTION_STYLE(context, styleId: number) {
      const searchParams = new URLSearchParams({ id: String(styleId) });
      const response = await fetch(
        `${makeURL('/api/v1/show/script/stage_direction_styles')}?${searchParams}`,
        { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        context.dispatch('GET_STAGE_DIRECTION_STYLES');
        VueToast.$toast.success('Deleted stage direction style!');
      } else {
        log.error('Unable to delete stage direction style');
        VueToast.$toast.error('Unable to delete stage direction style');
      }
    },
    async UPDATE_STAGE_DIRECTION_STYLE(context, style: Partial<StageDirectionStyle>) {
      const response = await fetch(`${makeURL('/api/v1/show/script/stage_direction_styles')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(style),
      });
      if (response.ok) {
        context.dispatch('GET_STAGE_DIRECTION_STYLES');
        VueToast.$toast.success('Updated stage direction style!');
      } else {
        log.error('Unable to edit stage direction style');
        VueToast.$toast.error('Unable to edit stage direction style');
      }
    },
    async GET_IMPORTABLE_STAGE_DIRECTION_STYLES() {
      const response = await fetch(
        `${makeURL('/api/v1/show/script/stage_direction_styles/import')}`,
        { method: 'GET' }
      );
      if (!response.ok) {
        log.error('Unable to fetch importable stage direction styles');
        throw new Error('Failed to fetch importable styles');
      }
      return response.json();
    },
    async GET_COMPILED_SCRIPTS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/script/compiled_scripts')}`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        const respJson = await response.json();
        context.commit('SET_COMPILED_SCRIPTS', respJson.scripts);
      } else {
        log.error('Unable to load compiled scripts');
      }
    },
  },
  getters: {
    SCRIPT_REVISIONS(state: ScriptState) {
      return state.revisions;
    },
    CURRENT_REVISION(state: ScriptState) {
      return state.currentRevision;
    },
    GET_SCRIPT_PAGE: (state: ScriptState) => (page: string | number) => {
      const pageStr = page.toString();
      if (Object.keys(state.script).includes(pageStr)) {
        return state.script[pageStr];
      }
      return [];
    },
    SCRIPT_CUES(state: ScriptState) {
      return state.cues;
    },
    SCRIPT_CUE_GROUPS(state: ScriptState) {
      return state.cueGroups;
    },
    GROUPED_CUES_FOR_LINE:
      (state: ScriptState) =>
      (
        lineId: number | null
      ): { individual: Cue[]; groups: { group: CueGroup; cues: Cue[] }[] } => {
        if (lineId == null) return { individual: [], groups: [] };
        const allCues = state.cues[String(lineId)] ?? [];
        const individual = allCues.filter((c) => c.group_id == null);
        const groupMap = new Map<number, Cue[]>();
        for (const cue of allCues) {
          if (cue.group_id != null) {
            if (!groupMap.has(cue.group_id)) groupMap.set(cue.group_id, []);
            groupMap.get(cue.group_id)!.push(cue);
          }
        }
        const groups: { group: CueGroup; cues: Cue[] }[] = [];
        for (const [groupId, cues] of groupMap) {
          const group = state.cueGroups.find((g) => g.id === groupId);
          if (group) {
            const sorted = [...cues].sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0));
            groups.push({ group, cues: sorted });
          }
        }
        return { individual, groups };
      },
    SCRIPT_CUTS(state: ScriptState) {
      return state.cuts;
    },
    STAGE_DIRECTION_STYLES(state: ScriptState) {
      return state.stageDirectionStyles;
    },
    COMPILED_SCRIPTS(state: ScriptState) {
      return state.compiledScripts;
    },
  },
};

export default module;
