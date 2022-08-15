import Vue from 'vue';
import * as $ from 'jquery';

import { makeURL } from '@/js/utils';

export default {
  state: {
    castList: [],
    characterList: [],
  },
  mutations: {
    SET_CAST_LIST(state, castList) {
      state.castList = castList;
    },
    SET_CHARACTER_LIST(state, characterList) {
      state.characterList = characterList;
    },
  },
  actions: {
    async GET_CAST_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/cast')}`);
      if (response.ok) {
        const cast = await response.json();
        context.commit('SET_CAST_LIST', cast.cast);
      } else {
        console.error('Unable to get cast list');
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
        console.error('Unable to add new cast member');
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
        console.error('Unable to delete cast member');
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
        console.error('Unable to edit cast member');
        Vue.$toast.error('Unable to edit cast member');
      }
    },
    async GET_CHARACTER_LIST(context) {
      const response = await fetch(`${makeURL('/api/v1/show/character')}`);
      if (response.ok) {
        const characters = await response.json();
        context.commit('SET_CHARACTER_LIST', characters.characters);
      } else {
        console.error('Unable to get characters list');
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
        console.error('Unable to add new character');
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
        console.error('Unable to delete character');
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
        console.error('Unable to edit character');
        Vue.$toast.error('Unable to edit character');
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
  },
};
