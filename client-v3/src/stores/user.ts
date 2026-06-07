import { defineStore } from 'pinia';
import log from 'loglevel';
import { isEmpty } from 'lodash';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
import { useWebSocketStore } from '@/stores/websocket';
import { useSystemStore } from '@/stores/system';
import router from '@/router';
import type { User, UserSettings, CueColourOverride } from '@/types/api/user';
import type { StageDirectionStyle } from '@/types/api/script';

const TOKEN_KEY = 'digiscript_auth_token';

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export const useUserStore = defineStore('user', {
  state: () => ({
    authToken: getToken(),
    currentUser: null as User | null,
    currentRbac: null as Record<string, [number, number][]> | null,
    users: [] as User[],
    tokenRefreshInterval: null as ReturnType<typeof setInterval> | null,
    userSettings: {} as UserSettings | Record<string, unknown>,
    stageDirectionStyleOverrides: [] as StageDirectionStyle[],
    cueColourOverrides: [] as CueColourOverride[],
  }),
  getters: {
    isAuthenticated: (state): boolean => state.authToken !== null,
  },
  actions: {
    _setToken(t: string): void {
      localStorage.setItem(TOKEN_KEY, t);
      this.authToken = t;
    },
    _clearToken(): void {
      localStorage.removeItem(TOKEN_KEY);
      this.authToken = null;
    },
    async login(username: string, password: string): Promise<boolean> {
      const wsStore = useWebSocketStore();

      const response = await fetch(makeURL('/api/v2/auth/login'), {
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
        if (data.access_token) this._setToken(data.access_token);

        try {
          await useSystemStore().getRbacRoles();
          await this.getCurrentUser();
          await this.getCurrentRbac();
          await this.getUserSettings();
          await this.setupTokenRefresh();
        } catch (e) {
          log.error('Error loading user data after login:', e);
          this._clearToken();
          toast.error('Login failed — unable to load user data. Please try again.');
          return false;
        }

        // Trigger WS authentication if the connection is waiting
        wsStore.triggerAuthentication();

        toast.success('Successfully logged in!');
        return true;
      }

      const responseBody = await response.json();
      log.error('Unable to log in');
      toast.error(`Unable to log in! ${responseBody.message}.`);
      return false;
    },

    async logout(): Promise<void> {
      if (this.tokenRefreshInterval) {
        clearInterval(this.tokenRefreshInterval);
        this.tokenRefreshInterval = null;
      }

      const token = this.authToken;
      this._clearToken();
      this.currentUser = null;
      this.currentRbac = null;
      this.userSettings = {};
      this.stageDirectionStyleOverrides = [];
      this.cueColourOverrides = [];

      useWebSocketStore().$patch({ authenticated: false, authSucceeded: false });

      if (token) {
        try {
          const response = await fetch(makeURL('/api/v2/auth/logout'), {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`, // use captured value since store is already cleared
            },
            body: JSON.stringify({ session_id: useWebSocketStore().internalUUID }),
          });
          if (!response.ok) {
            log.error('Logout response was not OK, but local state was cleared');
          }
        } catch (error) {
          log.error('Error during logout API call:', error);
        }
      }

      toast.success('Successfully logged out!');

      if (router.currentRoute.value.path !== '/') {
        router.push('/');
      }
    },

    async refreshToken(): Promise<boolean> {
      if (!this.authToken) return false;
      try {
        const response = await fetch(makeURL('/api/v2/auth/refresh-token'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        if (response.ok) {
          const data = await response.json();
          this._setToken(data.access_token);
          useWebSocketStore().refreshWsToken();
          log.debug('Token refreshed successfully');
          return true;
        }
        log.error('Failed to refresh token');
        return false;
      } catch (e) {
        log.error('Network error during token refresh:', e);
        return false;
      }
    },

    async tokenRefreshFromServer(newToken: string): Promise<void> {
      log.info('Received token refresh from server');
      if (newToken) {
        this._setToken(newToken);
        useWebSocketStore().refreshWsToken();
        log.info('Auth token updated from server');
      }
    },

    async getCurrentUser(): Promise<void> {
      const response = await fetch(makeURL('/api/v2/auth'));
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
      const response = await fetch(makeURL('/api/v2/users'));
      if (response.ok) {
        const data = await response.json();
        this.users = data.users;
      } else {
        log.error('Unable to get users');
        toast.error('Unable to fetch users!');
      }
    },

    async createUser(user: Record<string, unknown>): Promise<void> {
      const response = await fetch(makeURL('/api/v2/users'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user),
      });
      if (response.ok) {
        await this.getUsers();
        toast.success('User created!');
      } else {
        const body = await response.json();
        log.error('Unable to create user');
        toast.error(`Unable to create user: ${body.message || 'Unknown error'}`);
      }
    },

    async deleteUser(userId: number): Promise<void> {
      const params = new URLSearchParams({ id: String(userId) });
      const response = await fetch(makeURL(`/api/v2/users?${params}`), {
        method: 'DELETE',
      });
      if (response.ok) {
        await this.getUsers();
        toast.success('User deleted!');
      } else {
        const body = await response.json();
        log.error('Unable to delete user');
        toast.error(`Unable to delete user: ${body.message || 'Unknown error'}`);
      }
    },

    async changePassword(newPassword: string, oldPassword?: string): Promise<boolean> {
      const body: Record<string, string> = { new_password: newPassword };
      if (oldPassword) body.old_password = oldPassword;
      const response = await fetch(makeURL('/api/v2/users/password'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (response.ok) {
        const data = await response.json();
        if (data.access_token) this._setToken(data.access_token);
        await this.getCurrentUser();
        toast.success('Password changed successfully!');
        return true;
      }
      const error = await response.json();
      toast.error(error.message || 'Failed to change password');
      return false;
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
          if (this.authToken) {
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
      const response = await fetch(makeURL('/api/v2/users/token'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (response.ok) {
        toast.success('API token generated successfully!');
        return response.json();
      }
      const body = await response.json();
      toast.error(`Unable to generate API token: ${body.message || 'Unknown error'}`);
      return null;
    },

    async revokeApiToken(): Promise<boolean> {
      const response = await fetch(makeURL('/api/v2/users/token'), {
        method: 'DELETE',
      });
      if (response.ok) {
        toast.success('API token revoked successfully!');
        return true;
      }
      const body = await response.json();
      toast.error(`Unable to revoke API token: ${body.message || 'Unknown error'}`);
      return false;
    },

    async getApiToken(): Promise<Record<string, unknown> | null> {
      const response = await fetch(makeURL('/api/v2/users/token'));
      if (response.ok) return response.json();
      toast.error('Unable to get API token!');
      return null;
    },

    async editUser(user: { id: number; [key: string]: unknown }): Promise<void> {
      const params = new URLSearchParams({ id: String(user.id) });
      const response = await fetch(makeURL(`/api/v2/users?${params}`), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user),
      });
      if (response.ok) {
        await this.getUsers();
        toast.success('User updated!');
      } else {
        const body = await response.json();
        log.error('Unable to update user');
        toast.error(`Unable to update user: ${body.message || 'Unknown error'}`);
      }
    },

    async getStageDirectionStyleOverrides(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/user/settings/stage_direction_overrides'));
      if (response.ok) {
        const data = await response.json();
        this.stageDirectionStyleOverrides = data.overrides;
      } else {
        log.error('Unable to load stage direction style overrides');
      }
    },

    async addStageDirectionStyleOverride(style: Record<string, unknown>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/user/settings/stage_direction_overrides'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(style),
      });
      if (response.ok) {
        await this.getStageDirectionStyleOverrides();
        toast.success('Added new stage direction style override!');
      } else {
        log.error('Unable to add stage direction style override');
        toast.error('Unable to add new stage direction style override');
      }
    },

    async updateStageDirectionStyleOverride(style: Record<string, unknown>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/user/settings/stage_direction_overrides'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(style),
      });
      if (response.ok) {
        await this.getStageDirectionStyleOverrides();
        toast.success('Updated stage direction style override!');
      } else {
        log.error('Unable to edit stage direction style override');
        toast.error('Unable to edit stage direction style override');
      }
    },

    async deleteStageDirectionStyleOverride(styleId: number): Promise<void> {
      const response = await fetch(
        makeURL(`/api/v1/user/settings/stage_direction_overrides?id=${styleId}`),
        { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        await this.getStageDirectionStyleOverrides();
        toast.success('Deleted stage direction style override!');
      } else {
        log.error('Unable to delete stage direction style override');
        toast.error('Unable to delete stage direction style override');
      }
    },

    async getCueColourOverrides(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/user/settings/cue_colour_overrides'));
      if (response.ok) {
        const data = await response.json();
        this.cueColourOverrides = data.overrides;
      } else {
        log.error('Unable to load cue colour overrides');
      }
    },

    async addCueColourOverride(override: Record<string, unknown>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/user/settings/cue_colour_overrides'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(override),
      });
      if (response.ok) {
        await this.getCueColourOverrides();
        toast.success('Added new cue colour override!');
      } else {
        log.error('Unable to add cue colour override');
        toast.error('Unable to add new cue colour override');
      }
    },

    async updateCueColourOverride(override: Record<string, unknown>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/user/settings/cue_colour_overrides'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(override),
      });
      if (response.ok) {
        await this.getCueColourOverrides();
        toast.success('Updated cue colour override!');
      } else {
        log.error('Unable to edit cue colour override');
        toast.error('Unable to edit cue colour override');
      }
    },

    async deleteCueColourOverride(overrideId: number): Promise<void> {
      const response = await fetch(
        makeURL(`/api/v1/user/settings/cue_colour_overrides?id=${overrideId}`),
        { method: 'DELETE', headers: { 'Content-Type': 'application/json' } }
      );
      if (response.ok) {
        await this.getCueColourOverrides();
        toast.success('Deleted cue colour override!');
      } else {
        log.error('Unable to delete cue colour override');
        toast.error('Unable to delete cue colour override');
      }
    },
  },
});
