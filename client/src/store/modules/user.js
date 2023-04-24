import Vue from 'vue';
import log from 'loglevel';

import { makeURL } from '@/js/utils';

export default {
  state: {
    currentUser: null,
    showUsers: [],
  },
  mutations: {
    SET_CURRENT_USER(state, user) {
      state.currentUser = user;
    },
    SET_SHOW_USERS(state, users) {
      state.showUsers = users;
    },
  },
  actions: {
    async GET_USERS(context) {
      if (context.getters.CURRENT_USER == null || !context.getters.CURRENT_USER.is_admin
        || context.rootGetters.CURRENT_SHOW == null) {
        return;
      }
      const response = await fetch(`${makeURL('/api/v1/auth/users')}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      if (response.ok) {
        const users = await response.json();
        await context.commit('SET_SHOW_USERS', users.users);
      } else {
        log.error('Unable to get users');
        Vue.$toast.error('Unable to fetch users!');
      }
    },
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
        body: JSON.stringify({
          username: user.username,
          password: user.password,
          session_id: context.rootGetters.INTERNAL_UUID,
        }),
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
        body: JSON.stringify({
          session_id: context.rootGetters.INTERNAL_UUID,
        }),
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
    SHOW_USERS(state) {
      return state.showUsers;
    },
  },
};
