<template>
  <div v-if="!loading" class="config">
    <b-table-simple>
      <b-tbody>
        <b-tr>
          <b-td>
            <b>Version</b>
          </b-td>
          <b-td>
            {{ versionStatus.current_version || 'Unknown' }}
            <b-badge :variant="getVersionStatusVariant()" pill>
              {{ getVersionStatusText() }}
            </b-badge>
            <template v-if="versionStatus.update_available && versionStatus.latest_version">
              <br />
              <small class="text-muted">
                Latest: {{ versionStatus.latest_version }}
                <a
                  v-if="versionStatus.release_url"
                  :href="versionStatus.release_url"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  (Release Notes)
                </a>
              </small>
            </template>
            <template v-if="versionStatus.check_error">
              <br />
              <small class="text-danger">{{ versionStatus.check_error }}</small>
            </template>
          </b-td>
          <b-td>
            <b-button
              variant="outline-success"
              :disabled="isCheckingVersion"
              @click="checkForUpdates"
            >
              <b-spinner v-if="isCheckingVersion" small class="mr-1" />
              Check Now
            </b-button>
          </b-td>
        </b-tr>
        <b-tr>
          <b-td>
            <b>Connected Clients</b>
          </b-td>
          <b-td>
            {{ connectedClients.length }}
          </b-td>
          <b-td>
            <b-button v-b-modal.connected-clients variant="outline-success">
              View Clients
            </b-button>
          </b-td>
        </b-tr>
        <b-tr>
          <b-td><b>Hostname</b></b-td>
          <b-td>{{ systemInfo ? systemInfo.hostname : 'Unknown' }}</b-td>
          <b-td />
        </b-tr>
        <b-tr>
          <b-td><b>IP Address</b></b-td>
          <b-td>{{ systemInfo ? systemInfo.ip_address : 'Unknown' }}</b-td>
          <b-td />
        </b-tr>
        <b-tr>
          <b-td><b>Port</b></b-td>
          <b-td>{{ systemInfo ? systemInfo.port : 'Unknown' }}</b-td>
          <b-td />
        </b-tr>
      </b-tbody>
    </b-table-simple>
    <b-modal
      id="connected-clients"
      ref="connected-clients-modal"
      title="Connected Clients"
      size="lg"
    >
      <b-table
        id="connected-clients-table"
        :items="connectedClients"
        :fields="clientFields"
        :per-page="perPage"
        :current-page="currentPageClients"
        small
      />
      <pagination-controls
        :per-page.sync="perPage"
        :current-page.sync="currentPageClients"
        :total-rows="connectedClients.length"
        aria-controls="connected-clients-table"
      />
    </b-modal>
  </div>
  <div v-else class="text-center center-spinner">
    <b-spinner style="width: 10rem; height: 10rem" variant="info" />
  </div>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import log from 'loglevel';
import { makeURL } from '@/js/utils';

interface VersionStatus {
  current_version: string | null;
  latest_version: string | null;
  update_available: boolean;
  release_url: string | null;
  last_checked: string | null;
  check_error: string | null;
}

export default defineComponent({
  name: 'ConfigSystem',
  data() {
    return {
      perPage: 5,
      connectedClients: [] as unknown[],
      currentPageClients: 1,
      clientFields: [
        { key: 'internal_id', label: 'UUID' },
        { key: 'remote_ip', label: 'IP' },
        { key: 'is_editor', label: 'Editing Script' },
        'last_ping',
        'last_pong',
      ],
      clientTimeout: null as ReturnType<typeof setTimeout> | null,
      loading: true,
      versionStatus: {
        current_version: null,
        latest_version: null,
        update_available: false,
        release_url: null,
        last_checked: null,
        check_error: null,
      } as VersionStatus,
      isCheckingVersion: false,
      currentTime: Date.now(),
      timeUpdateInterval: null as ReturnType<typeof setInterval> | null,
      systemInfo: null as {
        hostname: string | null;
        ip_address: string | null;
        port: number | null;
      } | null,
    };
  },
  watch: {
    perPage() {
      this.currentPageClients = 1;
    },
  },
  async mounted() {
    await Promise.all([this.getConnectedClients(), this.getVersionStatus(), this.getSystemInfo()]);
    this.loading = false;
    this.timeUpdateInterval = setInterval(() => {
      this.currentTime = Date.now();
    }, 1000);
  },
  destroyed() {
    clearTimeout(this.clientTimeout ?? undefined);
    if (this.timeUpdateInterval) {
      clearInterval(this.timeUpdateInterval);
      this.timeUpdateInterval = null;
    }
  },
  methods: {
    async getConnectedClients(): Promise<void> {
      const response = await fetch(`${makeURL('/api/v1/ws/sessions')}`);
      if (response.ok) {
        const sessions = await response.json();
        this.connectedClients = sessions.sessions;
      } else {
        log.error('Unable to get available connected clients');
      }
      this.clientTimeout = setTimeout(this.getConnectedClients, 1000);
    },
    async getVersionStatus(): Promise<void> {
      try {
        const response = await fetch(`${makeURL('/api/v1/version/status')}`);
        if (response.ok) {
          this.versionStatus = await response.json();
        } else {
          log.error('Unable to get version status');
        }
      } catch (error) {
        log.error('Error fetching version status:', error);
      }
    },
    async checkForUpdates(): Promise<void> {
      if (this.isCheckingVersion) return;

      this.isCheckingVersion = true;

      try {
        const response = await fetch(`${makeURL('/api/v1/version/check')}`, { method: 'POST' });
        if (response.ok) {
          this.versionStatus = await response.json();
          if (this.versionStatus.update_available) {
            this.$toast.info(`Update available: ${this.versionStatus.latest_version}`);
          } else if (!this.versionStatus.check_error) {
            this.$toast.success('You are running the latest version');
          }
        } else {
          this.$toast.error('Unable to check for updates');
          log.error('Unable to check for updates');
        }
      } catch (error) {
        this.$toast.error('Unable to check for updates');
        log.error('Error checking for updates:', error);
      } finally {
        this.isCheckingVersion = false;
      }
    },
    getVersionStatusVariant(): string {
      if (!this.versionStatus.current_version) return 'secondary';
      if (this.versionStatus.check_error) return 'danger';
      if (this.versionStatus.update_available) return 'warning';
      return 'success';
    },
    getVersionStatusText(): string {
      if (!this.versionStatus.current_version) return 'Loading...';
      if (this.versionStatus.check_error) return 'Unable to check';
      if (this.versionStatus.update_available) return 'Update Available';
      return 'Up to date';
    },
    async getSystemInfo(): Promise<void> {
      try {
        const response = await fetch(`${makeURL('/api/v1/system/info')}`);
        if (response.ok) {
          this.systemInfo = await response.json();
        } else {
          log.error('Unable to get system info');
        }
      } catch (error) {
        log.error('Error fetching system info:', error);
      }
    },
    formatTimeAgo(isoTimestamp: string | null): string {
      if (!isoTimestamp) return 'Never';

      const timestamp = new Date(isoTimestamp).getTime();
      const seconds = Math.floor((this.currentTime - timestamp) / 1000);

      if (seconds < 10) return 'Just now';
      if (seconds < 60) return `${seconds} seconds ago`;
      if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
      if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
      return `${Math.floor(seconds / 86400)} days ago`;
    },
  },
});
</script>
