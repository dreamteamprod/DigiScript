import Vue from 'vue';
import log from 'loglevel';
import { isEmpty } from 'lodash';
import type { Module } from 'vuex';

import router from '@/router';
import { makeURL } from '@/js/utils';
import type { RootState } from '@/types/store';
import type { User } from '@/types/api/user';
import settings from './settings';

interface UserState {
  currentUser: User | null;
  currentRbac: Record<string, [number, number][]> | null;
  users: User[];
  authToken: string | null;
  tokenRefreshInterval: ReturnType<typeof setInterval> | null;
}

const VueToast = Vue as typeof Vue & {
  $toast: { success: (m: string) => void; error: (m: string) => void };
};

const module: Module<UserState, RootState> = {
  state: {
    currentUser: null,
    currentRbac: null,
    users: [],
    authToken: localStorage.getItem('digiscript_auth_token') || null,
    tokenRefreshInterval: null,
  },
  mutations: {
    SET_CURRENT_USER(state: UserState, user: User | null) {
      state.currentUser = user;
    },
    SET_USERS(state: UserState, users: User[]) {
      state.users = users;
    },
    SET_CURRENT_RBAC(state: UserState, rbac: Record<string, [number, number][]> | null) {
      state.currentRbac = rbac;
    },
    SET_AUTH_TOKEN(state: UserState, token: string | null) {
      state.authToken = token;
      if (token) {
        localStorage.setItem('digiscript_auth_token', token);
      } else {
        localStorage.removeItem('digiscript_auth_token');
      }
    },
    SET_TOKEN_REFRESH_INTERVAL(
      state: UserState,
      intervalId: ReturnType<typeof setInterval> | null
    ) {
      if (state.tokenRefreshInterval) {
        clearInterval(state.tokenRefreshInterval);
      }
      state.tokenRefreshInterval = intervalId;
    },
  },
  actions: {
    async GET_USERS(context) {
      if (context.getters.CURRENT_USER == null || !context.getters.CURRENT_USER.is_admin) {
        return;
      }
      const response = await fetch(makeURL('/api/v2/users'));
      if (response.ok) {
        const users = await response.json();
        await context.commit('SET_USERS', users.users);
      } else {
        log.error('Unable to get users');
        VueToast.$toast.error('Unable to fetch users!');
      }
    },
    async CREATE_USER(context, user) {
      const response = await fetch(makeURL('/api/v2/users'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user),
      });
      if (response.ok) {
        await context.dispatch('GET_USERS');
        VueToast.$toast.success('User created!');
      } else {
        const responseBody = await response.json();
        log.error('Unable to create user');
        VueToast.$toast.error(`Unable to create user: ${responseBody.message || 'Unknown error'}`);
      }
    },
    async DELETE_USER(context, userId: number) {
      const params = new URLSearchParams({ id: String(userId) });
      const response = await fetch(makeURL(`/api/v2/users?${params}`), {
        method: 'DELETE',
      });
      if (response.ok) {
        await context.dispatch('GET_USERS');
        VueToast.$toast.success('User deleted!');
      } else {
        const responseBody = await response.json();
        log.error('Unable to delete user');
        VueToast.$toast.error(`Unable to delete user: ${responseBody.message || 'Unknown error'}`);
      }
    },
    async USER_LOGIN(context, user: { username: string; password: string }) {
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
        VueToast.$toast.success('Successfully logged in!');
        return true;
      }
      const responseBody = await response.json();
      log.error('Unable to log in');
      VueToast.$toast.error(`Unable to log in! ${responseBody.message}.`);
      return false;
    },
    async TOKEN_REFRESH(context, payload: { DATA: { access_token: string } }) {
      log.info('Received token refresh from server');
      const newToken = payload.DATA.access_token;
      if (newToken) {
        await context.commit('SET_AUTH_TOKEN', newToken);
        await context.dispatch('REFRESH_WEBSOCKET_TOKEN');
        log.info('Auth token updated from server');
      }
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
            body: JSON.stringify({ session_id: context.rootGetters.INTERNAL_UUID }),
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
      VueToast.$toast.success('Successfully logged out!');
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
        log.error("Unable to get current user's RBAC roles");
      }
    },
    async SETUP_TOKEN_REFRESH(context) {
      if (context.state.tokenRefreshInterval) {
        clearInterval(context.state.tokenRefreshInterval);
      }
      const refreshInterval = setInterval(
        async () => {
          if (context.getters.AUTH_TOKEN) {
            await context.dispatch('REFRESH_TOKEN');
          } else {
            clearInterval(refreshInterval);
            await context.commit('SET_TOKEN_REFRESH_INTERVAL', null);
          }
        },
        1000 * 60 * 30
      );
      await context.commit('SET_TOKEN_REFRESH_INTERVAL', refreshInterval);
    },
    async GENERATE_API_TOKEN() {
      const response = await fetch(makeURL('/api/v2/users/token'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (response.ok) {
        const data = await response.json();
        VueToast.$toast.success('API token generated successfully!');
        return data;
      }
      const responseBody = await response.json();
      log.error('Unable to generate API token');
      VueToast.$toast.error(
        `Unable to generate API token: ${responseBody.message || 'Unknown error'}`
      );
      return null;
    },
    async REVOKE_API_TOKEN() {
      const response = await fetch(makeURL('/api/v2/users/token'), {
        method: 'DELETE',
      });
      if (response.ok) {
        VueToast.$toast.success('API token revoked successfully!');
        return true;
      }
      const responseBody = await response.json();
      log.error('Unable to revoke API token');
      VueToast.$toast.error(
        `Unable to revoke API token: ${responseBody.message || 'Unknown error'}`
      );
      return false;
    },
    async GET_API_TOKEN() {
      const response = await fetch(makeURL('/api/v2/users/token'), {
        method: 'GET',
      });
      if (response.ok) {
        return response.json();
      }
      log.error('Unable to get API token');
      VueToast.$toast.error('Unable to get API token!');
      return null;
    },
    async EDIT_USER(context, user: { id: number; [key: string]: unknown }) {
      const params = new URLSearchParams({ id: String(user.id) });
      const response = await fetch(makeURL(`/api/v2/users?${params}`), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user),
      });
      if (response.ok) {
        await context.dispatch('GET_USERS');
        VueToast.$toast.success('User updated!');
      } else {
        const responseBody = await response.json();
        log.error('Unable to update user');
        VueToast.$toast.error(`Unable to update user: ${responseBody.message || 'Unknown error'}`);
      }
    },
  },
  getters: {
    CURRENT_USER(state: UserState) {
      return state.currentUser;
    },
    USERS(state: UserState) {
      return state.users;
    },
    CURRENT_USER_RBAC(state: UserState) {
      return state.currentRbac;
    },
    AUTH_TOKEN(state: UserState) {
      return state.authToken;
    },
  },
  modules: {
    settings,
  },
};

export default module;
