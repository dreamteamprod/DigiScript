import Vue from 'vue';
import log from 'loglevel';
import { isEmpty } from 'lodash';

import router from '@/router';
import { makeURL } from '@/js/utils';
import settings from './settings';

export default {
  state: {
    currentUser: null,
    currentRbac: null,
    showUsers: [],
    authToken: localStorage.getItem('digiscript_auth_token') || null,
    tokenRefreshInterval: null,
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
    SET_TOKEN_REFRESH_INTERVAL(state, intervalId) {
      if (state.tokenRefreshInterval) {
        clearInterval(state.tokenRefreshInterval);
      }
      state.tokenRefreshInterval = intervalId;
    },
  },
  actions: {
    async GET_USERS(context) {
      if (context.getters.CURRENT_USER == null || !context.getters.CURRENT_USER.is_admin
        || context.rootGetters.CURRENT_SHOW == null) {
        return;
      }
      const response = await fetch(makeURL('/api/v1/auth/users'));
      if (response.ok) {
        const users = await response.json();
        await context.commit('SET_SHOW_USERS', users.users);
      } else {
        log.error('Unable to get users');
        Vue.$toast.error('Unable to fetch users!');
      }
    },
    async CREATE_USER(context, user) {
      const response = await fetch(makeURL('/api/v1/auth/create'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user),
      });
      if (response.ok) {
        await context.dispatch('GET_USERS');
        Vue.$toast.success('User created!');
      } else {
        const responseBody = await response.json();
        log.error('Unable to create user');
        Vue.$toast.error(`Unable to create user: ${responseBody.message || 'Unknown error'}`);
      }
    },
    async DELETE_USER(context, userId) {
      const response = await fetch(makeURL('/api/v1/auth/delete'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: userId }),
      });
      if (response.ok) {
        await context.dispatch('GET_USERS');
        Vue.$toast.success('User deleted!');
      } else {
        const responseBody = await response.json();
        log.error('Unable to delete user');
        Vue.$toast.error(`Unable to delete user: ${responseBody.message || 'Unknown error'}`);
      }
    },
    async USER_LOGIN(context, user) {
      const response = await fetch(makeURL('/api/v1/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: user.username,
          password: user.password,
          session_id: context.rootGetters.INTERNAL_UUID,
        }),
      });
      if (response.ok) {
        const data = await response.json();
        if (data.access_token) {
          await context.commit('SET_AUTH_TOKEN', data.access_token);
        }

        await context.dispatch('GET_RBAC_ROLES');
        await context.dispatch('GET_CURRENT_USER');
        await context.dispatch('GET_CURRENT_RBAC');
        await context.dispatch('GET_USER_SETTINGS');

        await context.dispatch('AUTHENTICATE_WEBSOCKET');
        await context.dispatch('SETUP_TOKEN_REFRESH');
        Vue.$toast.success('Successfully logged in!');
        return true;
      }
      const responseBody = await response.json();
      log.error('Unable to log in');
      Vue.$toast.error(`Unable to log in! ${responseBody.message}.`);
      return false;
    },
    async USER_LOGOUT(context) {
      if (context.state.tokenRefreshInterval) {
        clearInterval(context.state.tokenRefreshInterval);
        context.commit('SET_TOKEN_REFRESH_INTERVAL', null);
      }

      const token = context.state.authToken;

      await context.commit('SET_AUTH_TOKEN', null);
      await context.commit('SET_CURRENT_USER', null);
      await context.commit('SET_CURRENT_RBAC', null);
      await context.commit('SET_USER_SETTINGS', []);
      await context.commit('SET_STAGE_DIRECTION_STYLE_OVERRIDES', []);
      await context.commit('CLEAR_WS_AUTHENTICATION');

      if (token) {
        try {
          const response = await fetch(makeURL('/api/v1/auth/logout'), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({
              session_id: context.rootGetters.INTERNAL_UUID,
            }),
          });
          if (!response.ok) {
            log.error('Logout response was not OK, but local state was cleared');
          }
        } catch (error) {
          log.error('Error during logout API call:', error);
        }
      } else {
        log.info('Logout completed without API call - token already invalid');
      }
      Vue.$toast.success('Successfully logged out!');
      if (router.currentRoute.path !== '/') {
        router.push('/');
      }
    },
    async GET_CURRENT_USER(context) {
      const response = await fetch(makeURL('/api/v1/auth'));
      if (response.ok) {
        const user = await response.json();
        const userJson = isEmpty(user) ? null : user;
        await context.commit('SET_CURRENT_USER', userJson);
      } else {
        log.error('Unable to get current user');
      }
    },
    async REFRESH_TOKEN(context) {
      if (!context.getters.AUTH_TOKEN) return false;
      const response = await fetch(makeURL('/api/v1/auth/refresh-token'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (response.ok) {
        const data = await response.json();
        await context.commit('SET_AUTH_TOKEN', data.access_token);
        context.dispatch('REFRESH_WEBSOCKET_TOKEN');
        log.debug('Token refreshed successfully');
        return true;
      }
      log.error('Failed to refresh token');
      return false;
    },
    async GET_CURRENT_RBAC(context) {
      const response = await fetch(makeURL('/api/v1/rbac/user/roles'));
      if (response.ok) {
        const rbac = await response.json();
        await context.commit('SET_CURRENT_RBAC', rbac.roles);
      } else {
        log.error('Unable to get current user\'s RBAC roles');
      }
    },
    async SETUP_TOKEN_REFRESH(context) {
      if (context.state.tokenRefreshInterval) {
        clearInterval(context.state.tokenRefreshInterval);
      }
      const refreshInterval = setInterval(async () => {
        if (context.getters.AUTH_TOKEN) {
          await context.dispatch('REFRESH_TOKEN');
        } else {
          clearInterval(refreshInterval);
          await context.commit('SET_TOKEN_REFRESH_INTERVAL', null);
        }
      }, 1000 * 60 * 30);

      await context.commit('SET_TOKEN_REFRESH_INTERVAL', refreshInterval);
    },
    async GENERATE_API_TOKEN(context) {
      const response = await fetch(makeURL('/api/v1/auth/api-token/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (response.ok) {
        const data = await response.json();
        Vue.$toast.success('API token generated successfully!');
        return data;
      }
      const responseBody = await response.json();
      log.error('Unable to generate API token');
      Vue.$toast.error(`Unable to generate API token: ${responseBody.message || 'Unknown error'}`);
      return null;
    },
    async REVOKE_API_TOKEN(context) {
      const response = await fetch(makeURL('/api/v1/auth/api-token/revoke'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (response.ok) {
        Vue.$toast.success('API token revoked successfully!');
        return true;
      }
      const responseBody = await response.json();
      log.error('Unable to revoke API token');
      Vue.$toast.error(`Unable to revoke API token: ${responseBody.message || 'Unknown error'}`);
      return false;
    },
    async GET_API_TOKEN(context) {
      const response = await fetch(makeURL('/api/v1/auth/api-token'), {
        method: 'GET',
      });
      if (response.ok) {
        const data = await response.json();
        return data;
      }
      log.error('Unable to get API token');
      Vue.$toast.error('Unable to get API token!');
      return null;
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
