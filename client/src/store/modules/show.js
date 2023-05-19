import Vue from 'vue';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
  state: {
    castList: [],
    characterList: [],
    characterGroupList: [],
    actList: [],
    sceneList: [],
    cueTypes: [],
    sessions: [],
    currentSession: null,
  },
  mutations: {
    SET_CAST_LIST(state, castList) {
      state.castList = castList;
    },
    SET_CHARACTER_LIST(state, characterList) {
      state.characterList = characterList;
    },
    SET_CHARACTER_GROUP_LIST(state, characterGroupList) {
      state.characterGroupList = characterGroupList;
    },
    SET_ACT_LIST(state, actList) {
      state.actList = actList;
    },
    SET_SCENE_LIST(state, sceneList) {
      state.sceneList = sceneList;
    },
    SET_CUE_TYPES(state, cueTypes) {
      state.cueTypes = cueTypes;
    },
    CLEAR_CURRENT_SHOW(state) {
      state.castList = [];
      state.characterList = [];
      state.actList = [];
      state.sceneList = [];
    },
    SET_SESSIONS_LIST(state, sessions) {
      state.sessions = sessions;
    },
    SET_CURRENT_SESSION(state, session) {
      state.currentSession = session;
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
    async ADD_CAST_MEMBER(context, castMember) {
      const response = await fetch(`${makeURL('/api/v1/show/cast')}`, {
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
        log.error('Unable to add new cast member');
        Vue.$toast.error('Unable to add new cast member');
      }
    },
    async DELETE_CAST_MEMBER(context, castID) {
      const response = await fetch(`${makeURL('/api/v1/show/cast')}`, {
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
        log.error('Unable to delete cast member');
        Vue.$toast.error('Unable to delete cast member');
      }
    },
    async UPDATE_CAST_MEMBER(context, castMember) {
      const response = await fetch(`${makeURL('/api/v1/show/cast')}`, {
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
        log.error('Unable to edit cast member');
        Vue.$toast.error('Unable to edit cast member');
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
    async ADD_CHARACTER(context, character) {
      const response = await fetch(`${makeURL('/api/v1/show/character')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(character),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_LIST');
        Vue.$toast.success('Added new character!');
      } else {
        log.error('Unable to add new character');
        Vue.$toast.error('Unable to add new character');
      }
    },
    async DELETE_CHARACTER(context, characterID) {
      const response = await fetch(`${makeURL('/api/v1/show/character')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: characterID }),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_LIST');
        Vue.$toast.success('Deleted character!');
      } else {
        log.error('Unable to delete character');
        Vue.$toast.error('Unable to delete character');
      }
    },
    async UPDATE_CHARACTER(context, character) {
      const response = await fetch(`${makeURL('/api/v1/show/character')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(character),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_LIST');
        Vue.$toast.success('Updated character!');
      } else {
        log.error('Unable to edit character');
        Vue.$toast.error('Unable to edit character');
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
    async ADD_CHARACTER_GROUP(context, act) {
      const response = await fetch(`${makeURL('/api/v1/show/character/group')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_GROUP_LIST');
        Vue.$toast.success('Added new character group!');
      } else {
        log.error('Unable to add new character group');
        Vue.$toast.error('Unable to add new character group');
      }
    },
    async DELETE_CHARACTER_GROUP(context, characterGroupID) {
      const response = await fetch(`${makeURL('/api/v1/show/character/group')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: characterGroupID }),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_GROUP_LIST');
        Vue.$toast.success('Deleted character group!');
      } else {
        log.error('Unable to delete character group');
        Vue.$toast.error('Unable to delete character group');
      }
    },
    async UPDATE_CHARACTER_GROUP(context, characterGroup) {
      const response = await fetch(`${makeURL('/api/v1/show/character/group')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(characterGroup),
      });
      if (response.ok) {
        context.dispatch('GET_CHARACTER_GROUP_LIST');
        Vue.$toast.success('Updated character group!');
      } else {
        log.error('Unable to edit character group');
        Vue.$toast.error('Unable to edit character group');
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
    async ADD_ACT(context, act) {
      const response = await fetch(`${makeURL('/api/v1/show/act')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        context.dispatch('GET_ACT_LIST');
        Vue.$toast.success('Added new act!');
      } else {
        log.error('Unable to add new act');
        Vue.$toast.error('Unable to add new act');
      }
    },
    async DELETE_ACT(context, actID) {
      const response = await fetch(`${makeURL('/api/v1/show/act')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: actID }),
      });
      if (response.ok) {
        context.dispatch('GET_ACT_LIST');
        Vue.$toast.success('Deleted act!');
      } else {
        log.error('Unable to delete act');
        Vue.$toast.error('Unable to delete act');
      }
    },
    async UPDATE_ACT(context, act) {
      const response = await fetch(`${makeURL('/api/v1/show/act')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        context.dispatch('GET_ACT_LIST');
        Vue.$toast.success('Updated act!');
      } else {
        log.error('Unable to edit act');
        Vue.$toast.error('Unable to edit act');
      }
    },
    async SET_ACT_FIRST_SCENE(context, act) {
      const response = await fetch(`${makeURL('/api/v1/show/act/first_scene')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(act),
      });
      if (response.ok) {
        context.dispatch('GET_ACT_LIST');
        Vue.$toast.success('Updated act!');
      } else {
        log.error('Unable to edit act');
        Vue.$toast.error('Unable to edit act');
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
    async ADD_SCENE(context, scene) {
      const response = await fetch(`${makeURL('/api/v1/show/scene')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(scene),
      });
      if (response.ok) {
        context.dispatch('GET_SCENE_LIST');
        context.dispatch('GET_ACT_LIST');
        Vue.$toast.success('Added new scene!');
      } else {
        log.error('Unable to add new scene');
        Vue.$toast.error('Unable to add new scene');
      }
    },
    async DELETE_SCENE(context, sceneID) {
      const response = await fetch(`${makeURL('/api/v1/show/scene')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: sceneID }),
      });
      if (response.ok) {
        context.dispatch('GET_SCENE_LIST');
        context.dispatch('GET_ACT_LIST');
        Vue.$toast.success('Deleted scene!');
      } else {
        log.error('Unable to delete scene');
        Vue.$toast.error('Unable to delete scene');
      }
    },
    async UPDATE_SCENE(context, scene) {
      const response = await fetch(`${makeURL('/api/v1/show/scene')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(scene),
      });
      if (response.ok) {
        context.dispatch('GET_SCENE_LIST');
        context.dispatch('GET_ACT_LIST');
        Vue.$toast.success('Updated scene!');
      } else {
        log.error('Unable to edit scene');
        Vue.$toast.error('Unable to edit scene');
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
    async ADD_CUE_TYPE(context, cueType) {
      const response = await fetch(`${makeURL('/api/v1/show/cues/types')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(cueType),
      });
      if (response.ok) {
        context.dispatch('GET_CUE_TYPES');
        Vue.$toast.success('Added new cue type!');
      } else {
        log.error('Unable to add new cue type');
        Vue.$toast.error('Unable to add new cue type');
      }
    },
    async DELETE_CUE_TYPE(context, cueTypeID) {
      const response = await fetch(`${makeURL('/api/v1/show/cues/types')}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: cueTypeID }),
      });
      if (response.ok) {
        context.dispatch('GET_CUE_TYPES');
        Vue.$toast.success('Deleted cue type!');
      } else {
        log.error('Unable to delete cue type');
        Vue.$toast.error('Unable to delete cue type');
      }
    },
    async UPDATE_CUE_TYPE(context, cueType) {
      const response = await fetch(`${makeURL('/api/v1/show/cues/types')}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(cueType),
      });
      if (response.ok) {
        context.dispatch('GET_CUE_TYPES');
        Vue.$toast.success('Updated cue type!');
      } else {
        log.error('Unable to edit cue type');
        Vue.$toast.error('Unable to edit cue type');
      }
    },
    async GET_SHOW_SESSION_DATA(context) {
      const response = await fetch(`${makeURL('/api/v1/show/sessions')}`);
      if (response.ok) {
        const sessions = await response.json();
        context.commit('SET_SESSIONS_LIST', sessions.sessions);
        context.commit('SET_CURRENT_SESSION', sessions.current_session);
      } else {
        log.error('Unable to get show sessions');
      }
    },
  },
  getters: {
    CAST_LIST(state) {
      return state.castList;
    },
    CHARACTER_LIST(state) {
      return state.characterList;
    },
    CHARACTER_GROUP_LIST(state) {
      return state.characterGroupList;
    },
    ACT_LIST(state) {
      return state.actList;
    },
    ACT_DICT(state) {
      return Object.fromEntries(state.actList.map((act) => [act.id, act]));
    },
    ACT_BY_ID: (state, getters) => (actId) => {
      if (actId == null) {
        return null;
      }
      const actStr = actId.toString();
      if (Object.keys(getters.ACT_DICT).includes(actStr)) {
        return getters.ACT_DICT[actStr];
      }
      return null;
    },
    SCENE_LIST(state) {
      return state.sceneList;
    },
    SCENE_DICT(state) {
      return Object.fromEntries(state.sceneList.map((scene) => [scene.id, scene]));
    },
    SCENE_BY_ID: (state, getters) => (sceneId) => {
      if (sceneId == null) {
        return null;
      }
      const sceneStr = sceneId.toString();
      if (Object.keys(getters.SCENE_DICT).includes(sceneStr)) {
        return getters.SCENE_DICT[sceneStr];
      }
      return null;
    },
    CUE_TYPES(state) {
      return state.cueTypes;
    },
    SHOW_SESSIONS_LIST(state) {
      return state.sessions;
    },
    CURRENT_SHOW_SESSION(state) {
      return state.currentSession;
    },
  }
  ,
};
