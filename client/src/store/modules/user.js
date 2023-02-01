import Vue from 'vue';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
  state: {
    currentUser: null,
  },
  mutations: {
    SET_CURRENT_USER(state, user) {
      state.currentUser = user;
    },
  },
  actions: {
    async CREATE_USER(context, user) {
      const response = await fetch(`${makeURL('/api/v1/auth/create')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(user),
      });
      if (response.ok) {
        Vue.$toast.success('User created!');
      } else {
        log.error('Unable to create user');
        Vue.$toast.error('Unable to create user');
      }
    },
  },
  getters: {
    CURRENT_USER(state) {
      return state.currentUser;
    },
  },
};
