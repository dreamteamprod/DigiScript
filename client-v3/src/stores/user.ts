import { defineStore } from 'pinia';
import log from 'loglevel';
import { isEmpty } from 'lodash';
import { makeURL } from '@/js/utils';
import type { User, UserSettings, CueColourOverride } from '@/types/api/user';
import type { StageDirectionStyle } from '@/types/api/script';

const TOKEN_KEY = 'digiscript_auth_token';

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
function setToken(t: string): void {
  localStorage.setItem(TOKEN_KEY, t);
}
function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export const useUserStore = defineStore('user', {
  state: () => ({
    currentUser: null as User | null,
    currentRbac: null as Record<string, [number, number][]> | null,
    users: [] as User[],
    tokenRefreshInterval: null as ReturnType<typeof setInterval> | null,
    userSettings: {} as UserSettings | Record<string, unknown>,
    stageDirectionStyleOverrides: [] as StageDirectionStyle[],
    cueColourOverrides: [] as CueColourOverride[],
  }),
  getters: {
    authToken: (): string | null => getToken(),
    isAuthenticated: (): boolean => getToken() !== null,
  },
  actions: {
    async login(username: string, password: string): Promise<boolean> {
      const { useWebSocketStore } = await import('@/stores/websocket');
      const wsStore = useWebSocketStore();

      const response = await fetch(makeURL('/api/v1/auth/login'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          password,
          session_id: wsStore.internalUUID,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.access_token) setToken(data.access_token);

        const { useSystemStore } = await import('@/stores/system');
        await useSystemStore().getRbacRoles();
        await this.getCurrentUser();
        await this.getCurrentRbac();
        await this.getUserSettings();
        await this.setupTokenRefresh();

        // Trigger WS authentication if the connection is waiting
        wsStore.triggerAuthentication();

        const { useToast } = await import('vue-toast-notification');
        useToast().success('Successfully logged in!');
        return true;
      }

      const responseBody = await response.json();
      log.error('Unable to log in');
      const { useToast } = await import('vue-toast-notification');
      useToast().error(`Unable to log in! ${responseBody.message}.`);
      return false;
    },

    async logout(): Promise<void> {
      if (this.tokenRefreshInterval) {
        clearInterval(this.tokenRefreshInterval);
        this.tokenRefreshInterval = null;
      }

      const token = getToken();
      clearToken();
      this.currentUser = null;
      this.currentRbac = null;
      this.userSettings = {};
      this.stageDirectionStyleOverrides = [];

      const { useWebSocketStore } = await import('@/stores/websocket');
      useWebSocketStore().$patch({ authenticated: false, authSucceeded: false });

      if (token) {
        try {
          const { useWebSocketStore: getWsStore } = await import('@/stores/websocket');
          const response = await fetch(makeURL('/api/v1/auth/logout'), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,
            },
            body: JSON.stringify({ session_id: getWsStore().internalUUID }),
          });
          if (!response.ok) {
            log.error('Logout response was not OK, but local state was cleared');
          }
        } catch (error) {
          log.error('Error during logout API call:', error);
        }
      }

      const { useToast } = await import('vue-toast-notification');
      useToast().success('Successfully logged out!');

      const { default: router } = await import('@/router');
      if (router.currentRoute.value.path !== '/') {
        router.push('/');
      }
    },

    async refreshToken(): Promise<boolean> {
      if (!getToken()) return false;
      const response = await fetch(makeURL('/api/v1/auth/refresh-token'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (response.ok) {
        const data = await response.json();
        setToken(data.access_token);
        const { useWebSocketStore } = await import('@/stores/websocket');
        useWebSocketStore().refreshWsToken();
        log.debug('Token refreshed successfully');
        return true;
      }
      log.error('Failed to refresh token');
      return false;
    },

    async tokenRefreshFromServer(newToken: string): Promise<void> {
      log.info('Received token refresh from server');
      if (newToken) {
        setToken(newToken);
        const { useWebSocketStore } = await import('@/stores/websocket');
        useWebSocketStore().refreshWsToken();
        log.info('Auth token updated from server');
      }
    },

    async getCurrentUser(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/auth'));
      if (response.ok) {
        const user = await response.json();
        this.currentUser = isEmpty(user) ? null : user;
      } else {
        log.error('Unable to get current user');
      }
    },

    async getCurrentRbac(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/rbac/user/roles'));
      if (response.ok) {
        const data = await response.json();
        this.currentRbac = data.roles;
      } else {
        log.error("Unable to get current user's RBAC roles");
      }
    },

    async getUsers(): Promise<void> {
      if (!this.currentUser?.is_admin) return;
      const response = await fetch(makeURL('/api/v1/auth/users'));
      if (response.ok) {
        const data = await response.json();
        this.users = data.users;
      } else {
        log.error('Unable to get users');
        const { useToast } = await import('vue-toast-notification');
        useToast().error('Unable to fetch users!');
      }
    },

    async createUser(user: Record<string, unknown>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/auth/create'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user),
      });
      const { useToast } = await import('vue-toast-notification');
      if (response.ok) {
        await this.getUsers();
        useToast().success('User created!');
      } else {
        const body = await response.json();
        log.error('Unable to create user');
        useToast().error(`Unable to create user: ${body.message || 'Unknown error'}`);
      }
    },

    async deleteUser(userId: number): Promise<void> {
      const response = await fetch(makeURL('/api/v1/auth/delete'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: userId }),
      });
      const { useToast } = await import('vue-toast-notification');
      if (response.ok) {
        await this.getUsers();
        useToast().success('User deleted!');
      } else {
        const body = await response.json();
        log.error('Unable to delete user');
        useToast().error(`Unable to delete user: ${body.message || 'Unknown error'}`);
      }
    },

    async getUserSettings(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/user/settings'));
      if (response.ok) {
        this.userSettings = await response.json();
      } else {
        log.error('Unable to fetch user settings');
      }
    },

    async setupTokenRefresh(): Promise<void> {
      if (this.tokenRefreshInterval) clearInterval(this.tokenRefreshInterval);
      const refreshInterval = setInterval(
        async () => {
          if (getToken()) {
            await this.refreshToken();
          } else {
            clearInterval(refreshInterval);
            this.tokenRefreshInterval = null;
          }
        },
        1000 * 60 * 30
      );
      this.tokenRefreshInterval = refreshInterval;
    },

    async generateApiToken(): Promise<Record<string, unknown> | null> {
      const response = await fetch(makeURL('/api/v1/auth/api-token/generate'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const { useToast } = await import('vue-toast-notification');
      if (response.ok) {
        useToast().success('API token generated successfully!');
        return response.json();
      }
      const body = await response.json();
      useToast().error(`Unable to generate API token: ${body.message || 'Unknown error'}`);
      return null;
    },

    async revokeApiToken(): Promise<boolean> {
      const response = await fetch(makeURL('/api/v1/auth/api-token/revoke'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      const { useToast } = await import('vue-toast-notification');
      if (response.ok) {
        useToast().success('API token revoked successfully!');
        return true;
      }
      const body = await response.json();
      useToast().error(`Unable to revoke API token: ${body.message || 'Unknown error'}`);
      return false;
    },

    async getApiToken(): Promise<Record<string, unknown> | null> {
      const response = await fetch(makeURL('/api/v1/auth/api-token'));
      if (response.ok) return response.json();
      const { useToast } = await import('vue-toast-notification');
      useToast().error('Unable to get API token!');
      return null;
    },
  },
});
