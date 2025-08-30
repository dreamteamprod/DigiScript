import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export interface User {
  id: string;
  username: string;
  is_admin: boolean;
  // Add other user properties as needed
}

export interface RbacRole {
  id: string;
  name: string;
  permissions: string[];
  // Add other RBAC properties as needed
}

export interface UserSettings {
  [key: string]: unknown;
}

export interface StageDirectionStyleOverride {
  id: string;
  style: string;
  // Add other style override properties as needed
}

export const useAuthStore = defineStore('auth', () => {
  // State with localStorage persistence for auth token
  const currentUser = ref<User | null>(null);
  const currentRbac = ref<RbacRole[] | null>(null);
  const showUsers = ref<User[]>([]);
  const authToken = ref<string | null>(localStorage.getItem('digiscript_auth_token'));
  const tokenRefreshInterval = ref<number | null>(null);
  const userSettings = ref<UserSettings>({});
  const stageDirectionStyleOverrides = ref<StageDirectionStyleOverride[]>([]);

  // Getters
  const isAuthenticated = computed(() => !!authToken.value);
  const isAdmin = computed(() => currentUser.value?.is_admin || false);

  // Actions
  function setCurrentUser(user: User | null) {
    currentUser.value = user;
  }

  function setShowUsers(users: User[]) {
    showUsers.value = users;
  }

  function setCurrentRbac(rbac: RbacRole[] | null) {
    currentRbac.value = rbac;
  }

  function setAuthToken(token: string | null) {
    authToken.value = token;
    if (token) {
      localStorage.setItem('digiscript_auth_token', token);
    } else {
      localStorage.removeItem('digiscript_auth_token');
    }
  }

  function setTokenRefreshInterval(intervalId: number | null) {
    if (tokenRefreshInterval.value) {
      window.clearInterval(tokenRefreshInterval.value);
    }
    tokenRefreshInterval.value = intervalId;
  }

  function setUserSettings(settings: UserSettings) {
    userSettings.value = settings;
  }

  function setStageDirectionStyleOverrides(overrides: StageDirectionStyleOverride[]) {
    stageDirectionStyleOverrides.value = overrides;
  }

  // Clear all auth data (for logout)
  function clearAuthData() {
    currentUser.value = null;
    currentRbac.value = null;
    showUsers.value = [];
    setAuthToken(null);
    if (tokenRefreshInterval.value) {
      window.clearInterval(tokenRefreshInterval.value);
      tokenRefreshInterval.value = null;
    }
    userSettings.value = {};
    stageDirectionStyleOverrides.value = [];
  }

  // Utility function to create API URLs
  function makeURL(path: string): string {
    return `${window.location.protocol}//${window.location.hostname}:${window.location.port}${path}`;
  }

  // API Actions
  async function getUsers() {
    if (!currentUser.value?.is_admin) {
      return;
    }

    try {
      const response = await fetch(makeURL('/api/v1/auth/users'));
      if (response.ok) {
        const data = await response.json();
        setShowUsers(data.users);
      } else {
        console.error('Unable to get users');
        // TODO: Show error toast when toast functionality is added
      }
    } catch (error) {
      console.error('Error fetching users:', error);
    }
  }

  async function createUser(user: { username: string; password: string; is_admin: boolean }) {
    try {
      const response = await fetch(makeURL('/api/v1/auth/create'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(user),
      });

      if (response.ok) {
        await getUsers();
        // TODO: Show success toast
        console.log('User created successfully');
      } else {
        const responseBody = await response.json();
        console.error('Unable to create user:', responseBody.message);
        // TODO: Show error toast
      }
    } catch (error) {
      console.error('Error creating user:', error);
    }
  }

  async function deleteUser(userId: string) {
    try {
      const response = await fetch(makeURL('/api/v1/auth/delete'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: userId }),
      });

      if (response.ok) {
        await getUsers();
        // TODO: Show success toast
        console.log('User deleted successfully');
      } else {
        const responseBody = await response.json();
        console.error('Unable to delete user:', responseBody.message);
        // TODO: Show error toast
      }
    } catch (error) {
      console.error('Error deleting user:', error);
    }
  }

  async function getCurrentUser() {
    try {
      const response = await fetch(makeURL('/api/v1/auth'));
      if (response.ok) {
        const user = await response.json();
        setCurrentUser(Object.keys(user).length === 0 ? null : user);
      } else {
        console.error('Unable to get current user');
      }
    } catch (error) {
      console.error('Error fetching current user:', error);
    }
  }

  async function getCurrentRbac() {
    try {
      const response = await fetch(makeURL('/api/v1/rbac/user/roles'));
      if (response.ok) {
        const rbac = await response.json();
        setCurrentRbac(rbac.roles);
      } else {
        console.error('Unable to get current user\'s RBAC roles');
      }
    } catch (error) {
      console.error('Error fetching RBAC roles:', error);
    }
  }

  async function refreshToken(): Promise<boolean> {
    if (!authToken.value) return false;

    try {
      const response = await fetch(makeURL('/api/v1/auth/refresh-token'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      if (response.ok) {
        const data = await response.json();
        setAuthToken(data.access_token);
        // TODO: Refresh WebSocket token when WebSocket composable is ready
        console.log('Token refreshed successfully');
        return true;
      }
      console.error('Failed to refresh token');
      return false;
    } catch (error) {
      console.error('Error refreshing token:', error);
      return false;
    }
  }

  function setupTokenRefresh() {
    if (tokenRefreshInterval.value) {
      clearInterval(tokenRefreshInterval.value);
    }

    const refreshInterval = window.setInterval(async () => {
      if (authToken.value) {
        await refreshToken();
      } else {
        window.clearInterval(refreshInterval);
        setTokenRefreshInterval(null);
      }
    }, 1000 * 60 * 30); // 30 minutes

    setTokenRefreshInterval(refreshInterval);
  }

  async function getUserSettings() {
    try {
      const response = await fetch(makeURL('/api/v1/user/settings'));
      if (response.ok) {
        const settings = await response.json();
        setUserSettings(settings);
      } else {
        console.error('Unable to fetch user settings');
      }
    } catch (error) {
      console.error('Error fetching user settings:', error);
    }
  }

  async function getStageDirectionStyleOverrides() {
    try {
      const response = await fetch(makeURL('/api/v1/user/settings/stage_direction_overrides'), {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });

      if (response.ok) {
        const respJson = await response.json();
        setStageDirectionStyleOverrides(respJson.overrides);
      } else {
        console.error('Unable to load stage direction style overrides');
      }
    } catch (error) {
      console.error('Error fetching stage direction overrides:', error);
    }
  }

  async function addStageDirectionStyleOverride(style: unknown) {
    try {
      const response = await fetch(makeURL('/api/v1/user/settings/stage_direction_overrides'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(style),
      });

      if (response.ok) {
        await getStageDirectionStyleOverrides();
        // TODO: Show success toast
        console.log('Added new stage direction style override');
      } else {
        console.error('Unable to add new stage direction style override');
        // TODO: Show error toast
      }
    } catch (error) {
      console.error('Error adding stage direction override:', error);
    }
  }

  async function deleteStageDirectionStyleOverride(styleId: string) {
    try {
      const response = await fetch(makeURL('/api/v1/user/settings/stage_direction_overrides'), {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: styleId }),
      });

      if (response.ok) {
        await getStageDirectionStyleOverrides();
        // TODO: Show success toast
        console.log('Deleted stage direction style override');
      } else {
        console.error('Unable to delete stage direction style override');
        // TODO: Show error toast
      }
    } catch (error) {
      console.error('Error deleting stage direction override:', error);
    }
  }

  async function updateStageDirectionStyleOverride(style: unknown) {
    try {
      const response = await fetch(makeURL('/api/v1/user/settings/stage_direction_overrides'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(style),
      });

      if (response.ok) {
        await getStageDirectionStyleOverrides();
        // TODO: Show success toast
        console.log('Updated stage direction style override');
      } else {
        console.error('Unable to edit stage direction style override');
        // TODO: Show error toast
      }
    } catch (error) {
      console.error('Error updating stage direction override:', error);
    }
  }

  return {
    // State
    currentUser,
    currentRbac,
    showUsers,
    authToken,
    tokenRefreshInterval,
    userSettings,
    stageDirectionStyleOverrides,

    // Getters
    isAuthenticated,
    isAdmin,

    // Actions
    setCurrentUser,
    setShowUsers,
    setCurrentRbac,
    setAuthToken,
    setTokenRefreshInterval,
    setUserSettings,
    setStageDirectionStyleOverrides,
    clearAuthData,

    // API Actions
    getUsers,
    createUser,
    deleteUser,
    getCurrentUser,
    getCurrentRbac,
    refreshToken,
    setupTokenRefresh,
    getUserSettings,
    getStageDirectionStyleOverrides,
    addStageDirectionStyleOverride,
    deleteStageDirectionStyleOverride,
    updateStageDirectionStyleOverride,
  };
});
