import Vue from 'vue';
import log from 'loglevel';
import type { Module } from 'vuex';

import { makeURL } from '@/js/utils';
import { detectMicConflicts } from '@/js/micConflictUtils';
import type { RootState } from '@/types/store';
import type { Cast, Character, CharacterGroup, Act, Scene } from '@/types/api/show';
import type { CueType } from '@/types/api/cues';
import type { ShowSession, Interval, SessionTag } from '@/types/api/session';
import type { Microphone, MicrophoneAllocation } from '@/types/api/microphones';

interface ToastInstance {
  dismiss: () => void;
}

interface ScriptMode {
  key: string;
  value: number;
}

interface ShowState {
  castList: Cast[];
  characterList: Character[];
  characterGroupList: CharacterGroup[];
  actList: Act[];
  sceneList: Scene[];
  cueTypes: CueType[];
  sessions: ShowSession[];
  currentSession: ShowSession | null;
  currentInterval: Interval | null;
  sessionFollowData: Record<string, unknown>;
  microphones: Microphone[];
  micAllocations: MicrophoneAllocation[];
  noLeaderToast: ToastInstance | null;
  scriptModes: ScriptMode[];
  sessionTags: SessionTag[];
  stageManagerMode: boolean;
}

const VueToast = Vue as typeof Vue & {
  $toast: {
    success: (m: string) => void;
    error: (m: string, opts?: { duration: number }) => void;
    info: (m: string, opts?: { duration: number }) => void;
    warning: (m: string, opts?: { duration: number }) => ToastInstance;
  };
};

const module: Module<ShowState, RootState> = {
  state: {
    castList: [],
    characterList: [],
    characterGroupList: [],
    actList: [],
    sceneList: [],
    cueTypes: [],
    sessions: [],
    currentSession: null,
    currentInterval: null,
    sessionFollowData: {},
    microphones: [],
    micAllocations: [],
    noLeaderToast: null,
    scriptModes: [],
    sessionTags: [],
    stageManagerMode: false,
  },
  mutations: {
    SET_CAST_LIST(state: ShowState, castList: Cast[]) {
      state.castList = castList;
    },
    SET_CHARACTER_LIST(state: ShowState, characterList: Character[]) {
      state.characterList = characterList;
    },
    SET_CHARACTER_GROUP_LIST(state: ShowState, characterGroupList: CharacterGroup[]) {
      state.characterGroupList = characterGroupList;
    },
    SET_ACT_LIST(state: ShowState, actList: Act[]) {
      state.actList = actList;
    },
    SET_SCENE_LIST(state: ShowState, sceneList: Scene[]) {
      state.sceneList = sceneList;
    },
    SET_CUE_TYPES(state: ShowState, cueTypes: CueType[]) {
      state.cueTypes = cueTypes;
    },
    CLEAR_CURRENT_SHOW(state: ShowState) {
      state.castList = [];
      state.characterList = [];
      state.actList = [];
      state.sceneList = [];
      state.sessionTags = [];
    },
    SET_SESSIONS_LIST(state: ShowState, sessions: ShowSession[]) {
      state.sessions = sessions;
    },
    SET_CURRENT_SESSION(state: ShowState, session: ShowSession | null) {
      state.currentSession = session;
    },
    SET_CURRENT_INTERVAL(state: ShowState, interval: Interval | null) {
      state.currentInterval = interval;
    },
    SET_SESSION_FOLLOW_DATA(state: ShowState, data: Record<string, unknown>) {
      state.sessionFollowData = data;
    },
    SET_MIC_LIST(state: ShowState, micList: Microphone[]) {
      state.microphones = micList;
    },
    SET_MIC_ALLOCATIONS_LIST(state: ShowState, micAllocations: MicrophoneAllocation[]) {
      state.micAllocations = micAllocations;
    },
    SET_TOAST_INSTANCE(state: ShowState, toast: ToastInstance | null) {
      state.noLeaderToast = toast;
    },
    UPDATE_SCRIPT_MODES(state: ShowState, modes: ScriptMode[]) {
      state.scriptModes = modes;
    },
    SET_SESSION_TAGS(state: ShowState, tags: SessionTag[]) {
      state.sessionTags = tags;
    },
    SET_STAGE_MANAGER_MODE(state: ShowState, enabled: boolean) {
      state.stageManagerMode = enabled;
    },
  },
  actions: {
    async GET_CAST_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/cast')}`);
      if (response.ok) {
        const cast = await response.json();
        context.commit('SET_CAST_LIST', cast.cast);
      } else {
        log.error('Unable to get cast list');
      }
    },
    async ADD_CAST_MEMBER(context, castMember: Partial<Cast>) {
      const response = await fetch(`${makeURL('/api/v1/show/cast')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(castMember),
      });
      if (response.ok) {
        context.dispatch('GET_CAST_LIST');
        VueToast.$toast.success('Added new cast member!');
      } else {
        log.error('Unable to add new cast member');
        VueToast.$toast.error('Unable to add new cast member');
      }
    },
    async DELETE_CAST_MEMBER(context, castID: number) {
      const searchParams = new URLSearchParams({ id: String(castID) });
      const response = await fetch(`${makeURL('/api/v1/show/cast')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_CAST_LIST');
        VueToast.$toast.success('Deleted cast member!');
      } else {
        log.error('Unable to delete cast member');
        VueToast.$toast.error('Unable to delete cast member');
      }
    },
    async UPDATE_CAST_MEMBER(context, castMember: Partial<Cast>) {
      const response = await fetch(`${makeURL('/api/v1/show/cast')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(castMember),
      });
      if (response.ok) {
        context.dispatch('GET_CAST_LIST');
        VueToast.$toast.success('Updated cast member!');
      } else {
        log.error('Unable to edit cast member');
        VueToast.$toast.error('Unable to edit cast member');
      }
    },
    async GET_CHARACTER_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/character')}`);
      if (response.ok) {
        const characters = await response.json();
        context.commit('SET_CHARACTER_LIST', characters.characters);
      } else {
        log.error('Unable to get characters list');
      }
    },
    async ADD_CHARACTER(context, character: Partial<Character>) {
      const response = await fetch(`${makeURL('/api/v1/show/character')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(character),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_LIST');
        VueToast.$toast.success('Added new character!');
      } else {
        log.error('Unable to add new character');
        VueToast.$toast.error('Unable to add new character');
      }
    },
    async DELETE_CHARACTER(context, characterID: number) {
      const searchParams = new URLSearchParams({ id: String(characterID) });
      const response = await fetch(`${makeURL('/api/v1/show/character')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_LIST');
        VueToast.$toast.success('Deleted character!');
      } else {
        log.error('Unable to delete character');
        VueToast.$toast.error('Unable to delete character');
      }
    },
    async MERGE_CHARACTER(
      context,
      { source_id, destination_id }: { source_id: number; destination_id: number }
    ) {
      const response = await fetch(makeURL('/api/v1/show/character/merge'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_id, destination_id }),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_GROUP_LIST');
        VueToast.$toast.success('Merged character!');
      } else {
        log.error('Unable to merge characters');
        VueToast.$toast.error('Unable to merge characters');
      }
    },
    async UPDATE_CHARACTER(context, character: Partial<Character>) {
      const response = await fetch(`${makeURL('/api/v1/show/character')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(character),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_LIST');
        VueToast.$toast.success('Updated character!');
      } else {
        log.error('Unable to edit character');
        VueToast.$toast.error('Unable to edit character');
      }
    },
    async GET_CHARACTER_GROUP_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/character/group')}`);
      if (response.ok) {
        const groups = await response.json();
        context.commit('SET_CHARACTER_GROUP_LIST', groups.character_groups);
        context.dispatch('GET_CHARACTER_LIST');
      } else {
        log.error('Unable to get characters list');
      }
    },
    async ADD_CHARACTER_GROUP(context, act: Partial<CharacterGroup>) {
      const response = await fetch(`${makeURL('/api/v1/show/character/group')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_GROUP_LIST');
        VueToast.$toast.success('Added new character group!');
      } else {
        log.error('Unable to add new character group');
        VueToast.$toast.error('Unable to add new character group');
      }
    },
    async DELETE_CHARACTER_GROUP(context, characterGroupID: number) {
      const searchParams = new URLSearchParams({ id: String(characterGroupID) });
      const response = await fetch(`${makeURL('/api/v1/show/character/group')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_GROUP_LIST');
        VueToast.$toast.success('Deleted character group!');
      } else {
        log.error('Unable to delete character group');
        VueToast.$toast.error('Unable to delete character group');
      }
    },
    async UPDATE_CHARACTER_GROUP(context, characterGroup: Partial<CharacterGroup>) {
      const response = await fetch(`${makeURL('/api/v1/show/character/group')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(characterGroup),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_GROUP_LIST');
        VueToast.$toast.success('Updated character group!');
      } else {
        log.error('Unable to edit character group');
        VueToast.$toast.error('Unable to edit character group');
      }
    },
    async GET_ACT_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/act')}`);
      if (response.ok) {
        const acts = await response.json();
        context.commit('SET_ACT_LIST', acts.acts);
      } else {
        log.error('Unable to get acts list');
      }
    },
    async ADD_ACT(context, act: Partial<Act>) {
      const response = await fetch(`${makeURL('/api/v1/show/act')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        context.dispatch('GET_ACT_LIST');
        VueToast.$toast.success('Added new act!');
      } else {
        log.error('Unable to add new act');
        VueToast.$toast.error('Unable to add new act');
      }
    },
    async DELETE_ACT(context, actID: number) {
      const searchParams = new URLSearchParams({ id: String(actID) });
      const response = await fetch(`${makeURL('/api/v1/show/act')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_ACT_LIST');
        VueToast.$toast.success('Deleted act!');
      } else {
        log.error('Unable to delete act');
        VueToast.$toast.error('Unable to delete act');
      }
    },
    async UPDATE_ACT(context, act: Partial<Act>) {
      const response = await fetch(`${makeURL('/api/v1/show/act')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        context.dispatch('GET_ACT_LIST');
        VueToast.$toast.success('Updated act!');
      } else {
        log.error('Unable to edit act');
        VueToast.$toast.error('Unable to edit act');
      }
    },
    async SET_ACT_FIRST_SCENE(context, act: Partial<Act>) {
      const response = await fetch(`${makeURL('/api/v1/show/act/first_scene')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        context.dispatch('GET_ACT_LIST');
        VueToast.$toast.success('Updated act!');
      } else {
        log.error('Unable to edit act');
        VueToast.$toast.error('Unable to edit act');
      }
    },
    async GET_SCENE_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/scene')}`);
      if (response.ok) {
        const scenes = await response.json();
        context.commit('SET_SCENE_LIST', scenes.scenes);
      } else {
        log.error('Unable to get scenes list');
      }
    },
    async ADD_SCENE(context, scene: Partial<Scene>) {
      const response = await fetch(`${makeURL('/api/v1/show/scene')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scene),
      });
      if (response.ok) {
        context.dispatch('GET_SCENE_LIST');
        context.dispatch('GET_ACT_LIST');
        VueToast.$toast.success('Added new scene!');
      } else {
        log.error('Unable to add new scene');
        VueToast.$toast.error('Unable to add new scene');
      }
    },
    async DELETE_SCENE(context, sceneID: number) {
      const searchParams = new URLSearchParams({ id: String(sceneID) });
      const response = await fetch(`${makeURL('/api/v1/show/scene')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_SCENE_LIST');
        context.dispatch('GET_ACT_LIST');
        VueToast.$toast.success('Deleted scene!');
      } else {
        log.error('Unable to delete scene');
        VueToast.$toast.error('Unable to delete scene');
      }
    },
    async UPDATE_SCENE(context, scene: Partial<Scene>) {
      const response = await fetch(`${makeURL('/api/v1/show/scene')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scene),
      });
      if (response.ok) {
        context.dispatch('GET_SCENE_LIST');
        context.dispatch('GET_ACT_LIST');
        VueToast.$toast.success('Updated scene!');
      } else {
        log.error('Unable to edit scene');
        VueToast.$toast.error('Unable to edit scene');
      }
    },
    async GET_CUE_TYPES(context) {
      const response = await fetch(`${makeURL('/api/v1/show/cues/types')}`);
      if (response.ok) {
        const cueTypes = await response.json();
        context.commit('SET_CUE_TYPES', cueTypes.cue_types);
      } else {
        log.error('Unable to get cue types');
      }
    },
    async ADD_CUE_TYPE(context, cueType: Partial<CueType>) {
      const response = await fetch(`${makeURL('/api/v1/show/cues/types')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cueType),
      });
      if (response.ok) {
        context.dispatch('GET_CUE_TYPES');
        VueToast.$toast.success('Added new cue type!');
      } else {
        log.error('Unable to add new cue type');
        VueToast.$toast.error('Unable to add new cue type');
      }
    },
    async DELETE_CUE_TYPE(context, cueTypeID: number) {
      const searchParams = new URLSearchParams({ id: String(cueTypeID) });
      const response = await fetch(`${makeURL('/api/v1/show/cues/types')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_CUE_TYPES');
        VueToast.$toast.success('Deleted cue type!');
      } else {
        log.error('Unable to delete cue type');
        VueToast.$toast.error('Unable to delete cue type');
      }
    },
    async UPDATE_CUE_TYPE(context, cueType: Partial<CueType>) {
      const response = await fetch(`${makeURL('/api/v1/show/cues/types')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cueType),
      });
      if (response.ok) {
        context.dispatch('GET_CUE_TYPES');
        VueToast.$toast.success('Updated cue type!');
      } else {
        log.error('Unable to edit cue type');
        VueToast.$toast.error('Unable to edit cue type');
      }
    },
    async GET_IMPORTABLE_CUE_TYPES() {
      const response = await fetch(`${makeURL('/api/v1/show/cues/types/import')}`, {
        method: 'GET',
      });
      if (!response.ok) {
        log.error('Unable to fetch importable cue types');
        throw new Error('Failed to fetch importable cue types');
      }
      return response.json();
    },
    async GET_SHOW_SESSION_DATA(context) {
      const response = await fetch(`${makeURL('/api/v1/show/sessions')}`);
      if (response.ok) {
        const sessions = await response.json();
        context.commit('SET_SESSIONS_LIST', sessions.sessions);
        context.commit('SET_CURRENT_SESSION', sessions.current_session);
        context.commit('SET_CURRENT_INTERVAL', sessions.current_interval);
        if (
          context.getters.NO_LEADER_TOAST &&
          context.getters.CURRENT_SHOW_SESSION.client_internal_id != null
        ) {
          context.getters.NO_LEADER_TOAST.dismiss();
          context.commit('SET_TOAST_INSTANCE', null);
        }
      } else {
        log.error('Unable to get show sessions');
      }
    },
    async ELECTED_LEADER(_context, _payload: unknown) {
      VueToast.$toast.info(
        'You are now leader of the script - other clients will follow your view',
        { duration: 0 }
      );
    },
    async NO_LEADER(context, _payload: unknown) {
      await context.dispatch('GET_SHOW_SESSION_DATA');
      if (context.getters.NO_LEADER_TOAST == null) {
        const instance = VueToast.$toast.warning(
          'There is no script leader. Please scroll your own script!',
          { duration: 0 }
        );
        context.commit('SET_TOAST_INSTANCE', instance);
      }
    },
    SCRIPT_SCROLL(context, payload: { DATA: Record<string, unknown> }) {
      context.commit('SET_SESSION_FOLLOW_DATA', payload.DATA);
    },
    async GET_MICROPHONE_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/microphones')}`);
      if (response.ok) {
        const mics = await response.json();
        context.commit('SET_MIC_LIST', mics.microphones);
      } else {
        log.error('Unable to get microphone list');
      }
    },
    async ADD_MICROPHONE(context, microphone: Partial<Microphone>) {
      const response = await fetch(`${makeURL('/api/v1/show/microphones')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(microphone),
      });
      if (response.ok) {
        context.dispatch('GET_MICROPHONE_LIST');
        VueToast.$toast.success('Added new microphone!');
      } else {
        log.error('Unable to add new microphone');
        VueToast.$toast.error('Unable to add new microphone');
      }
    },
    async DELETE_MICROPHONE(context, microphoneId: number) {
      const searchParams = new URLSearchParams({ id: String(microphoneId) });
      const response = await fetch(`${makeURL('/api/v1/show/microphones')}?${searchParams}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_MICROPHONE_LIST');
        VueToast.$toast.success('Deleted microphone!');
      } else {
        log.error('Unable to delete microphone');
        VueToast.$toast.error('Unable to delete microphone');
      }
    },
    async UPDATE_MICROPHONE(context, microphone: Partial<Microphone>) {
      const response = await fetch(`${makeURL('/api/v1/show/microphones')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(microphone),
      });
      if (response.ok) {
        context.dispatch('GET_MICROPHONE_LIST');
        VueToast.$toast.success('Updated microphone!');
      } else {
        log.error('Unable to edit microphone');
        VueToast.$toast.error('Unable to edit microphone');
      }
    },
    async GET_MIC_ALLOCATIONS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/microphones/allocations')}`);
      if (response.ok) {
        const micAllocs = await response.json();
        context.commit('SET_MIC_ALLOCATIONS_LIST', micAllocs.allocations);
      } else {
        log.error('Unable to get microphone allocations');
      }
    },
    async UPDATE_MIC_ALLOCATIONS(context, allocations: unknown) {
      const response = await fetch(`${makeURL('/api/v1/show/microphones/allocations')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(allocations),
      });
      if (response.ok) {
        context.dispatch('GET_MIC_ALLOCATIONS');
        VueToast.$toast.success('Updated microphone allocations!');
      } else {
        log.error('Unable to edit microphone allocations');
        VueToast.$toast.error('Unable to edit microphone allocations');
      }
    },
    async GET_SCRIPT_MODES(context) {
      const response = await fetch(makeURL('/api/v1/show/script_modes'));
      if (response.ok) {
        const rbac = await response.json();
        await context.commit('UPDATE_SCRIPT_MODES', rbac.script_modes);
      } else {
        log.error('Unable to fetch script modes');
      }
    },
    async GET_SESSION_TAGS(context) {
      const response = await fetch(`${makeURL('/api/v1/show/session/tags')}`);
      if (response.ok) {
        const data = await response.json();
        context.commit('SET_SESSION_TAGS', data.tags);
      } else {
        log.error('Unable to get session tags');
      }
    },
    async ADD_SESSION_TAG(context, tag: Partial<SessionTag>) {
      const response = await fetch(`${makeURL('/api/v1/show/session/tags')}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tag),
      });
      if (response.ok) {
        context.dispatch('GET_SESSION_TAGS');
        VueToast.$toast.success('Added new session tag!');
      } else {
        log.error('Unable to add session tag');
        VueToast.$toast.error('Unable to add session tag');
      }
    },
    async UPDATE_SESSION_TAG(context, tag: Partial<SessionTag>) {
      const response = await fetch(`${makeURL('/api/v1/show/session/tags')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(tag),
      });
      if (response.ok) {
        context.dispatch('GET_SESSION_TAGS');
        VueToast.$toast.success('Updated session tag!');
      } else {
        log.error('Unable to edit session tag');
        VueToast.$toast.error('Unable to edit session tag');
      }
    },
    async DELETE_SESSION_TAG(context, tagId: number) {
      const response = await fetch(`${makeURL('/api/v1/show/session/tags')}?id=${tagId}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        context.dispatch('GET_SESSION_TAGS');
        VueToast.$toast.success('Deleted session tag!');
      } else {
        log.error('Unable to delete session tag');
        VueToast.$toast.error('Unable to delete session tag');
      }
    },
    async GET_IMPORTABLE_SESSION_TAGS() {
      const response = await fetch(`${makeURL('/api/v1/show/session/tags/import')}`, {
        method: 'GET',
      });
      if (!response.ok) {
        log.error('Unable to fetch importable session tags');
        throw new Error('Failed to fetch importable session tags');
      }
      return response.json();
    },
    async UPDATE_SESSION_TAGS(
      context,
      { sessionId, tagIds }: { sessionId: number; tagIds: number[] }
    ) {
      const response = await fetch(`${makeURL('/api/v1/show/sessions/assign-tags')}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, tag_ids: tagIds }),
      });
      if (response.ok) {
        await context.dispatch('GET_SHOW_SESSION_DATA');
        VueToast.$toast.success('Updated session tags!');
      } else {
        const errorData = await response.json().catch(() => ({}));
        log.error('Unable to update session tags:', errorData);
        VueToast.$toast.error(errorData.message || 'Unable to update session tags');
        throw new Error('Failed to update session tags');
      }
    },
  },
  getters: {
    CAST_LIST(state: ShowState) {
      return state.castList;
    },
    CAST_DICT(state: ShowState) {
      return Object.fromEntries(state.castList.map((cast) => [cast.id, cast]));
    },
    CAST_BY_ID: (_state: ShowState, getters) => (castId: number | null) => {
      if (castId == null) return null;
      const castStr = castId.toString();
      if (Object.keys(getters.CAST_DICT).includes(castStr)) {
        return getters.CAST_DICT[castStr];
      }
      return null;
    },
    CHARACTER_LIST(state: ShowState) {
      return state.characterList;
    },
    CHARACTER_DICT(state: ShowState) {
      return Object.fromEntries(state.characterList.map((character) => [character.id, character]));
    },
    CHARACTER_BY_ID: (_state: ShowState, getters) => (characterId: number | null) => {
      if (characterId == null) return null;
      const characterStr = characterId.toString();
      if (Object.keys(getters.CHARACTER_DICT).includes(characterStr)) {
        return getters.CHARACTER_DICT[characterStr];
      }
      return null;
    },
    CHARACTER_GROUP_LIST(state: ShowState) {
      return state.characterGroupList;
    },
    ACT_LIST(state: ShowState) {
      return state.actList;
    },
    ACT_DICT(state: ShowState) {
      return Object.fromEntries(state.actList.map((act) => [act.id, act]));
    },
    ACT_BY_ID: (_state: ShowState, getters) => (actId: number | null) => {
      if (actId == null) return null;
      const actStr = actId.toString();
      if (Object.keys(getters.ACT_DICT).includes(actStr)) {
        return getters.ACT_DICT[actStr];
      }
      return null;
    },
    SCENE_LIST(state: ShowState) {
      return state.sceneList;
    },
    SCENE_DICT(state: ShowState) {
      return Object.fromEntries(state.sceneList.map((scene) => [scene.id, scene]));
    },
    SCENE_BY_ID: (_state: ShowState, getters) => (sceneId: number | null) => {
      if (sceneId == null) return null;
      const sceneStr = sceneId.toString();
      if (Object.keys(getters.SCENE_DICT).includes(sceneStr)) {
        return getters.SCENE_DICT[sceneStr];
      }
      return null;
    },
    CUE_TYPES(state: ShowState) {
      return state.cueTypes;
    },
    CUE_TYPES_DICT(state: ShowState) {
      return Object.fromEntries(state.cueTypes.map((cueType) => [cueType.id, cueType]));
    },
    CUE_TYPE_BY_ID: (_state: ShowState, getters) => (cueTypeId: number | null) => {
      if (cueTypeId == null) return null;
      const cueTypeStr = cueTypeId.toString();
      if (Object.keys(getters.CUE_TYPES_DICT).includes(cueTypeStr)) {
        return getters.CUE_TYPES_DICT[cueTypeStr];
      }
      return null;
    },
    SHOW_SESSIONS_LIST(state: ShowState) {
      return state.sessions;
    },
    CURRENT_SHOW_SESSION(state: ShowState) {
      return state.currentSession;
    },
    CURRENT_SHOW_INTERVAL(state: ShowState) {
      return state.currentInterval;
    },
    SESSION_FOLLOW_DATA(state: ShowState) {
      return state.sessionFollowData;
    },
    MICROPHONES(state: ShowState) {
      return state.microphones;
    },
    MICROPHONE_DICT(state: ShowState) {
      return Object.fromEntries(state.microphones.map((mic) => [mic.id, mic]));
    },
    MICROPHONE_BY_ID: (_state: ShowState, getters) => (micId: number | null) => {
      if (micId == null) return null;
      const micStr = micId.toString();
      if (Object.keys(getters.MICROPHONE_DICT).includes(micStr)) {
        return getters.MICROPHONE_DICT[micStr];
      }
      return null;
    },
    MIC_ALLOCATIONS(state: ShowState) {
      return state.micAllocations;
    },
    ORDERED_SCENES(_state: ShowState, getters) {
      if (
        !getters.CURRENT_SHOW?.first_act_id ||
        !getters.SCENE_LIST?.length ||
        !getters.ACT_LIST?.length
      ) {
        return [];
      }

      const scenes: Scene[] = [];
      let currentAct = getters.ACT_BY_ID(getters.CURRENT_SHOW.first_act_id);

      while (currentAct != null) {
        let currentScene = getters.SCENE_BY_ID(currentAct.first_scene);
        while (currentScene != null) {
          scenes.push(currentScene);
          currentScene = getters.SCENE_BY_ID(currentScene.next_scene);
        }
        currentAct = getters.ACT_BY_ID(currentAct.next_act);
      }

      return scenes;
    },
    MIC_CONFLICTS(_state: ShowState, getters) {
      const allocationsObj: Record<string, Record<number, number>> = {};
      Object.keys(getters.MIC_ALLOCATIONS).forEach((micId) => {
        const allocs = getters.MIC_ALLOCATIONS[micId];
        const sceneData: Record<number, number> = {};
        if (Array.isArray(allocs)) {
          allocs.forEach((alloc: { scene_id: number; character_id: number }) => {
            sceneData[alloc.scene_id] = alloc.character_id;
          });
        }
        allocationsObj[micId] = sceneData;
      });

      return detectMicConflicts(
        allocationsObj,
        getters.SCENE_LIST,
        getters.ACT_LIST,
        getters.CURRENT_SHOW,
        getters.CHARACTER_LIST,
        getters.CAST_LIST
      );
    },
    CONFLICTS_BY_SCENE(_state: ShowState, getters) {
      return getters.MIC_CONFLICTS.conflictsByScene || {};
    },
    CONFLICTS_BY_MIC(_state: ShowState, getters) {
      return getters.MIC_CONFLICTS.conflictsByMic || {};
    },
    MIC_TIMELINE_DATA(_state: ShowState, getters) {
      return {
        scenes: getters.ORDERED_SCENES,
        allocations: getters.MIC_ALLOCATIONS,
        conflicts: getters.MIC_CONFLICTS.conflicts || [],
        microphones: getters.MICROPHONES,
        characters: getters.CHARACTER_LIST,
      };
    },
    NO_LEADER_TOAST(state: ShowState) {
      return state.noLeaderToast;
    },
    SCRIPT_MODES(state: ShowState) {
      return state.scriptModes;
    },
    SESSION_TAGS(state: ShowState) {
      return state.sessionTags;
    },
    SESSION_TAGS_DICT(state: ShowState) {
      return Object.fromEntries(state.sessionTags.map((tag) => [tag.id, tag]));
    },
    SESSION_TAG_BY_ID: (_state: ShowState, getters) => (tagId: number | null) => {
      if (tagId == null) return null;
      const tagStr = tagId.toString();
      if (Object.keys(getters.SESSION_TAGS_DICT).includes(tagStr)) {
        return getters.SESSION_TAGS_DICT[tagStr];
      }
      return null;
    },
    STAGE_MANAGER_MODE(state: ShowState) {
      return state.stageManagerMode;
    },
  },
};

export default module;
