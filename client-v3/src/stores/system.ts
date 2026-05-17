import { defineStore } from 'pinia';
import log from 'loglevel';
import { makeURL } from '@/js/utils';
import { toast } from '@/js/toast';
import type { Show } from '@/types/api/show';
import type { SystemSettings } from '@/types/api/settings';
import { useUserStore } from '@/stores/user';

interface ConnectedSession {
  internal_id: string;
  remote_ip: string;
  is_editor: boolean;
  last_ping: string | null;
  last_pong: string | null;
}

interface VersionStatus {
  current_version: string | null;
  latest_version: string | null;
  update_available: boolean;
  release_url: string | null;
  last_checked: string | null;
  check_error: string | null;
}

interface RbacRole {
  key: string;
  value: number;
}

type UserRbac = Record<string, [number, number][]> | null;

function getUserRbac(): UserRbac {
  return useUserStore().currentRbac;
}

function getRbacMask(roles: RbacRole[], key: string): number {
  return roles.find((x) => x.key === key)?.value ?? 0;
}

export const useSystemStore = defineStore('system', {
  state: () => ({
    settings: {} as SystemSettings | Record<string, never>,
    availableShows: [] as Show[],
    rawSettings: {} as Record<string, unknown>,
    rbacRoles: [] as RbacRole[],
    settingsCategories: {} as Record<string, unknown>,
    currentShow: null as Show | null,
    connectedSessions: [] as ConnectedSession[],
    versionStatus: null as VersionStatus | null,
  }),
  getters: {
    isAdminUser(): boolean {
      return useUserStore().currentUser?.is_admin === true;
    },
    isShowEditor(): boolean {
      if (this.isAdminUser) return true;
      if (this.rbacRoles.length === 0) return false;
      const userRbac = getUserRbac();
      if (!userRbac?.shows) return false;
      return (userRbac.shows[0][1] & getRbacMask(this.rbacRoles, 'WRITE')) !== 0;
    },
    isShowReader(): boolean {
      if (this.isAdminUser) return true;
      if (this.rbacRoles.length === 0) return false;
      const userRbac = getUserRbac();
      if (!userRbac?.shows) return false;
      return (userRbac.shows[0][1] & getRbacMask(this.rbacRoles, 'READ')) !== 0;
    },
    isShowExecutor(): boolean {
      if (this.isAdminUser) return true;
      if (this.rbacRoles.length === 0) return false;
      const userRbac = getUserRbac();
      if (!userRbac?.shows) return false;
      return (userRbac.shows[0][1] & getRbacMask(this.rbacRoles, 'EXECUTE')) !== 0;
    },
    isScriptEditor(): boolean {
      if (this.isAdminUser) return true;
      if (this.rbacRoles.length === 0) return false;
      const userRbac = getUserRbac();
      if (!userRbac?.script) return false;
      return (userRbac.script[0][1] & getRbacMask(this.rbacRoles, 'WRITE')) !== 0;
    },
    isScriptReader(): boolean {
      if (this.isAdminUser) return true;
      if (this.rbacRoles.length === 0) return false;
      const userRbac = getUserRbac();
      if (!userRbac?.script) return false;
      return (userRbac.script[0][1] & getRbacMask(this.rbacRoles, 'READ')) !== 0;
    },
    isCueEditor(): boolean {
      if (this.isAdminUser) return true;
      if (this.rbacRoles.length === 0) return false;
      const userRbac = getUserRbac();
      if (!userRbac?.cuetypes) return false;
      const writeMask = getRbacMask(this.rbacRoles, 'WRITE');
      return userRbac.cuetypes.filter((x) => (x[1] & writeMask) !== 0).length > 0;
    },
    isCueReader(): boolean {
      if (this.isAdminUser) return true;
      if (this.rbacRoles.length === 0) return false;
      const userRbac = getUserRbac();
      if (!userRbac?.cuetypes) return false;
      const readMask = getRbacMask(this.rbacRoles, 'READ');
      return userRbac.cuetypes.filter((x) => (x[1] & readMask) !== 0).length > 0;
    },
    isAllowedShowConfig(): boolean {
      return (
        this.isAdminUser ||
        this.isShowEditor ||
        this.isShowReader ||
        this.isShowExecutor ||
        this.isScriptReader ||
        this.isScriptEditor ||
        this.isCueReader ||
        this.isCueEditor
      );
    },
    hasShowAccess(): boolean {
      if (!this.currentShow) return false;
      if (this.isAdminUser) return true;
      const userRbac = getUserRbac();
      if (!userRbac) return false;

      const writeMask = getRbacMask(this.rbacRoles, 'WRITE');
      const readMask = getRbacMask(this.rbacRoles, 'READ');
      const execMask = getRbacMask(this.rbacRoles, 'EXECUTE');

      const showAllowed =
        userRbac.shows?.[0] && (userRbac.shows[0][1] & (writeMask | execMask | readMask)) !== 0;
      const scriptAllowed =
        userRbac.script?.[0] && (userRbac.script[0][1] & (writeMask | readMask)) !== 0;
      const cueTypesAllowed =
        userRbac.cuetypes &&
        userRbac.cuetypes.filter((x) => (x[1] & (writeMask | readMask)) !== 0).length > 0;

      return !!(showAllowed || scriptAllowed || cueTypesAllowed);
    },
  },
  actions: {
    async getAvailableShows() {
      const response = await fetch(makeURL('/api/v1/shows'));
      if (response.ok) {
        const data = await response.json();
        this.availableShows = data.shows;
      } else {
        log.error('Unable to get available shows');
      }
    },
    async getRawSettings() {
      const response = await fetch(makeURL('/api/v1/settings/raw'));
      if (response.ok) {
        this.rawSettings = await response.json();
      } else {
        log.error('Unable to get raw settings');
      }
    },
    async getSettings() {
      const response = await fetch(makeURL('/api/v1/settings'));
      if (response.ok) {
        const data = await response.json();
        await this.updateSettings(data);
      } else {
        log.error('Unable to fetch settings');
      }
    },
    async updateSettings(payload: SystemSettings) {
      this.settings = payload;
      await this.settingsChanged();
    },
    async settingsChanged() {
      await this.getRawSettings();

      if (this.settings.current_show) {
        const response = await fetch(makeURL('/api/v1/show'));
        if (response.ok) {
          this.currentShow = await response.json();
        } else {
          log.error('Unable to fetch current show');
        }
      } else {
        this.currentShow = null;
      }
    },
    async getShowDetails(): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show'));
      if (response.ok) {
        this.currentShow = await response.json();
      } else {
        log.error('Unable to get show details');
      }
    },
    async updateShow(showDetails: Partial<Show>): Promise<void> {
      const response = await fetch(makeURL('/api/v1/show'), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(showDetails),
      });
      if (response.ok) {
        await this.getShowDetails();
        toast.success('Updated show!');
      } else {
        log.error('Unable to edit show');
        toast.error('Unable to edit show');
      }
    },
    async getRbacRoles() {
      const response = await fetch(makeURL('/api/v1/rbac/roles'));
      if (response.ok) {
        const data = await response.json();
        this.rbacRoles = data.roles;
      } else {
        log.error('Unable to fetch RBAC roles');
      }
    },
    async getSettingsCategories() {
      const response = await fetch(makeURL('/api/v1/settings/categories'));
      if (response.ok) {
        const data = await response.json();
        this.settingsCategories = data.categories;
      } else {
        log.error('Unable to fetch settings categories');
      }
    },
    async getConnectedSessions() {
      const response = await fetch(makeURL('/api/v1/ws/sessions'));
      if (response.ok) {
        const data = await response.json();
        this.connectedSessions = data.sessions ?? [];
      } else {
        log.error('Unable to fetch connected sessions');
      }
    },
    async getVersionStatus() {
      const response = await fetch(makeURL('/api/v1/version/status'));
      if (response.ok) {
        this.versionStatus = await response.json();
      } else {
        log.error('Unable to fetch version status');
      }
    },
    async checkForUpdates() {
      const response = await fetch(makeURL('/api/v1/version/check'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      if (response.ok) {
        this.versionStatus = await response.json();
      } else {
        log.error('Unable to check for updates');
      }
    },
  },
});
