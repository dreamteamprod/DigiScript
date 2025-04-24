import Vue from 'vue';
import log from 'loglevel';

import { makeURL } from '@/js/utils';
import router from '@/router';
import { isEmpty } from 'lodash';
import settings from './settings';

export default {
  state: {
    currentUser: null,
    currentRbac: null,
    showUsers: [],
    authToken: localStorage.getItem('digiscript_auth_token') || null,
  },
  mutations: {
    SET_CURRENT_USER(state, user) {
      state.currentUser = user;
    },
    SET_SHOW_USERS(state, users) {
      state.showUsers = users;
    },
    SET_CURRENT_RBAC(state, rbac) {
      state.currentRbac = rbac;
    },
    SET_AUTH_TOKEN(state, token) {
      state.authToken = token;
      if (token) {
        localStorage.setItem('digiscript_auth_token', token);
      } else {
        localStorage.removeItem('digiscript_auth_token');
      }
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
        await context.dispatch('GET_USERS');
        Vue.$toast.success('User created!');
      } else {
        log.error('Unable to create user');
        Vue.$toast.error('Unable to create user');
      }
    },
    async DELETE_USER(context, userId) {
      const response = await fetch(`${makeURL('/api/v1/auth/delete')}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ id: userId }),
      });
      if (response.ok) {
        await context.dispatch('GET_USERS');
        Vue.$toast.success('User deleted!');
      } else {
        log.error('Unable to delete user');
        Vue.$toast.error('Unable to delete user');
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
        const data = await response.json();
        // Store the JWT token
        if (data.access_token) {
          await context.commit('SET_AUTH_TOKEN', data.access_token);
        }

        // Get user data and permissions
        context.dispatch('GET_RBAC_ROLES');
        context.dispatch('GET_CURRENT_USER');
        context.dispatch('GET_CURRENT_RBAC');
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
        // Clear the token and user data
        await context.commit('SET_AUTH_TOKEN', null);
        await context.commit('SET_CURRENT_USER', null);

        Vue.$toast.success('Successfully logged out!');
        if (router.currentRoute.path !== '/') {
          router.push('/');
        }
      } else {
        log.error('Unable to log out');
        Vue.$toast.error('Unable to log out!');
      }
    },
    async GET_CURRENT_USER(context) {
      const response = await fetch(`${makeURL('/api/v1/auth')}`);
      if (response.ok) {
        const user = await response.json();
        const userJson = isEmpty(user) ? null : user;
        await context.commit('SET_CURRENT_USER', userJson);
      } else {
        log.error('Unable to get current user');
      }
    },
    async REFRESH_TOKEN(context) {
      if (!context.getters.AUTH_TOKEN) return;

      try {
        const response = await fetch(`${makeURL('/api/v1/auth/refresh-token')}`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${context.getters.AUTH_TOKEN}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          await context.commit('SET_AUTH_TOKEN', data.access_token);
        } else {
          await context.dispatch('USER_LOGOUT');
        }
      } catch (error) {
        log.error('Token refresh failed', error);
      }
    },
    async GET_CURRENT_RBAC(context) {
      const response = await fetch(`${makeURL('/api/v1/rbac/user/roles')}`);
      if (response.ok) {
        const rbac = await response.json();
        await context.commit('SET_CURRENT_RBAC', rbac.roles);
      } else {
        log.error('Unable to get current user\'s RBAC roles');
      }
    },
    SETUP_TOKEN_REFRESH(context) {
      // Refresh token every 30 minutes if the user is logged in
      setInterval(() => {
        if (context.getters.AUTH_TOKEN) {
          context.dispatch('REFRESH_TOKEN');
        }
      }, 1000 * 60 * 30);
    },
  },
  getters: {
    CURRENT_USER(state) {
      return state.currentUser;
    },
    SHOW_USERS(state) {
      return state.showUsers;
    },
    CURRENT_USER_RBAC(state) {
      return state.currentRbac;
    },
    AUTH_TOKEN(state) {
      return state.authToken;
    },
  },
  modules: {
    settings,
  },
};
