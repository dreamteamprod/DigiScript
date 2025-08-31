import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

export interface SystemSettings {
  has_admin_user: boolean;
  current_show: string | null;
  debug_mode: boolean;
  // Add other settings as needed
  [key: string]: unknown;
}

export interface RawSetting {
  value: unknown;
  type: 'int' | 'str' | 'bool';
  display_name: string;
  help_text: string;
  can_edit: boolean;
}

export interface ShowData {
  id: string;
  name: string;
  start_date: string;
  end_date: string;
  created_at: string;
}

export interface ConnectedClient {
  internal_id: string;
  remote_ip: string;
  is_editor: boolean;
  last_ping: string;
  last_pong: string;
}

export const useSettingsStore = defineStore('settings', () => {
  // State
  const settings = ref<SystemSettings>({
    has_admin_user: false,
    current_show: null,
    debug_mode: false,
  });
  const rawSettings = ref<Record<string, RawSetting>>({});
  const availableShows = ref<ShowData[]>([]);
  const currentShow = ref<ShowData | null>(null);
  const rbacRoles = ref<unknown[]>([]);
  const connectedClients = ref<ConnectedClient[]>([]);
  const isSubmittingSettings = ref(false);
  const settingsForm = ref<Record<string, unknown>>({});

  // Getters
  const debugModeEnabled = computed(() => settings.value.debug_mode);
  const hasAdminUser = computed(() => settings.value.has_admin_user);
  const currentShowLoaded = computed(() => (
    settings.value.current_show != null && currentShow.value != null
  ));

  // Utility function to create API URLs
  function makeURL(path: string): string {
    return `${window.location.protocol}//${window.location.hostname}:${window.location.port}${path}`;
  }

  // Actions
  function updateSettings(newSettings: SystemSettings) {
    settings.value = { ...newSettings };
  }

  function updateShows(shows: ShowData[]) {
    availableShows.value = shows;
  }

  function updateRawSettings(newRawSettings: Record<string, RawSetting>) {
    rawSettings.value = newRawSettings;
    // Initialize settings form with current values
    const formData: Record<string, unknown> = {};
    Object.keys(newRawSettings).forEach((key) => {
      formData[key] = newRawSettings[key].value;
    });
    settingsForm.value = formData;
  }

  function updateRbacRoles(rbac: unknown[]) {
    rbacRoles.value = rbac;
  }

  function setCurrentShow(show: ShowData | null) {
    currentShow.value = show;
  }

  function clearCurrentShow() {
    currentShow.value = null;
  }

  function updateConnectedClients(clients: ConnectedClient[]) {
    connectedClients.value = clients;
  }

  function resetSettingsForm() {
    const formData: Record<string, unknown> = {};
    Object.keys(rawSettings.value).forEach((key) => {
      formData[key] = rawSettings.value[key].value;
    });
    settingsForm.value = formData;
  }

  // API Actions
  async function getRawSettings() {
    try {
      const response = await fetch(makeURL('/api/v1/settings/raw'));
      if (response.ok) {
        const rawSettingsData = await response.json();
        updateRawSettings(rawSettingsData);
      } else {
        console.error('Unable to get system settings');
      }
    } catch (error) {
      console.error('Error fetching raw settings:', error);
    }
  }

  async function settingsChanged() {
    await getRawSettings();

    if (settings.value.current_show) {
      const currShowId = settings.value.current_show;
      if (!currentShow.value || currentShow.value.id !== currShowId) {
        try {
          const response = await fetch(makeURL('/api/v1/show'));
          if (response.ok) {
            const show = await response.json();
            setCurrentShow(show);
          } else {
            console.error('Unable to set current show');
          }
        } catch (error) {
          console.error('Error fetching current show:', error);
        }
      }
    } else {
      setCurrentShow(null);
      clearCurrentShow();
    }
  }

  async function getSettings() {
    try {
      const response = await fetch(makeURL('/api/v1/settings'));
      if (response.ok) {
        const settingsData = await response.json();
        updateSettings(settingsData);
        await settingsChanged();
      } else {
        console.error('Unable to fetch settings');
      }
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  }

  async function getRbacRoles() {
    try {
      const response = await fetch(makeURL('/api/v1/rbac/roles'));
      if (response.ok) {
        const rbac = await response.json();
        updateRbacRoles(rbac.roles);
      } else {
        console.error('Unable to fetch RBAC roles');
      }
    } catch (error) {
      console.error('Error fetching RBAC roles:', error);
    }
  }

  async function updateSystemSettings(
    settingsData: Record<string, unknown>,
  ): Promise<{ success: boolean; error?: string }> {
    if (isSubmittingSettings.value) {
      return { success: false, error: 'Already submitting settings' };
    }

    isSubmittingSettings.value = true;

    try {
      const response = await fetch(makeURL('/api/v1/settings'), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(settingsData),
      });

      if (response.ok) {
        // Update the form with saved values
        settingsForm.value = { ...settingsData };
        return { success: true };
      }
      const errorText = await response.text();
      console.error('Unable to save settings:', errorText);
      return { success: false, error: 'Unable to save settings' };
    } catch (error) {
      console.error('Error saving settings:', error);
      return { success: false, error: 'Network error while saving settings' };
    } finally {
      isSubmittingSettings.value = false;
    }
  }

  async function getAvailableShows(): Promise<void> {
    try {
      const response = await fetch(makeURL('/api/v1/shows'));
      if (response.ok) {
        const data = await response.json();
        updateShows(data.shows);
      } else {
        console.error('Unable to get available shows');
      }
    } catch (error) {
      console.error('Error fetching available shows:', error);
    }
  }

  async function getConnectedClients(): Promise<void> {
    try {
      const response = await fetch(makeURL('/api/v1/ws/sessions'));
      if (response.ok) {
        const data = await response.json();
        updateConnectedClients(data.sessions);
      } else {
        console.error('Unable to get connected clients');
      }
    } catch (error) {
      console.error('Error fetching connected clients:', error);
    }
  }

  async function loadShow(showId: string): Promise<{ success: boolean; error?: string }> {
    try {
      const response = await fetch(makeURL('/api/v1/settings'), {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          current_show: showId,
        }),
      });

      if (response.ok) {
        return { success: true };
      }
      const errorText = await response.text();
      console.error('Unable to load show:', errorText);
      return { success: false, error: 'Unable to load show' };
    } catch (error) {
      console.error('Error loading show:', error);
      return { success: false, error: 'Network error while loading show' };
    }
  }

  return {
    // State
    settings,
    rawSettings,
    availableShows,
    currentShow,
    rbacRoles,
    connectedClients,
    isSubmittingSettings,
    settingsForm,

    // Getters
    debugModeEnabled,
    hasAdminUser,
    currentShowLoaded,

    // Actions
    updateSettings,
    updateShows,
    updateRawSettings,
    updateRbacRoles,
    setCurrentShow,
    clearCurrentShow,
    updateConnectedClients,
    resetSettingsForm,

    // API Actions
    getRawSettings,
    getSettings,
    settingsChanged,
    getRbacRoles,
    updateSystemSettings,
    getAvailableShows,
    getConnectedClients,
    loadShow,
  };
});
