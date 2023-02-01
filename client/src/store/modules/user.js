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
    async USER_LOGIN(context, user) {
      const response = await fetch(`${makeURL('/api/v1/auth/login')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(user),
      });
      if (response.ok) {
        context.dispatch('GET_CURRENT_USER');
        Vue.$toast.success('Successfully logged in!');
        return true;
      }
      const responseBody = await response.json();
      log.error('Unable to log in');
      Vue.$toast.error(`Unable to log in! ${responseBody.message}.`);
      return false;
    },
    async USER_LOGOUT(context) {
      const response = await fetch(`${makeURL('/api/v1/auth/logout')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        await context.commit('SET_CURRENT_USER', null);
        Vue.$toast.success('Successfully logged out!');
      } else {
        log.error('Unable to log out');
        Vue.$toast.error('Unable to log out!');
      }
    },
    async GET_CURRENT_USER(context) {
      const response = await fetch(`${makeURL('/api/v1/auth')}`);
      if (response.ok) {
        const user = await response.json();
        await context.commit('SET_CURRENT_USER', user);
      } else {
        log.error('Unable to get current user');
      }
    },
  },
  getters: {
    CURRENT_USER(state) {
      return state.currentUser;
    },
  },
};
