<template>
  <b-container class="mx-0" fluid>
    <!-- Header -->
    <b-row style="margin-top: 1rem">
      <b-col>
        <h3>Connect to DigiScript Server</h3>
        <p class="text-muted">
          Select a saved connection, discover servers on your network, or add a new server manually.
        </p>
      </b-col>
    </b-row>

    <!-- Saved Connections -->
    <b-row style="margin-top: 2rem">
      <b-col>
        <b-card no-body class="mb-3">
          <b-card-header header-tag="header" class="p-3">
            <div class="d-flex justify-content-between align-items-center">
              <div class="d-flex align-items-center">
                <h6 class="mb-0 mr-2">Saved Connections</h6>
                <template v-if="!savedConnsCollapsed">
                  <!-- Available servers (green) -->
                  <b-badge v-if="availableServersCount > 0" variant="success" pill class="mr-1">
                    {{ availableServersCount }}
                  </b-badge>

                  <!-- Incompatible servers (warning) -->
                  <b-badge v-if="incompatibleServersCount > 0" variant="warning" pill class="mr-1">
                    {{ incompatibleServersCount }}
                  </b-badge>

                  <!-- Unavailable servers (danger) -->
                  <b-badge v-if="unavailableServersCount > 0" variant="danger" pill class="mr-1">
                    {{ unavailableServersCount }}
                  </b-badge>

                  <!-- Show total if no status checks yet -->
                  <b-badge
                    v-if="Object.keys(serverStatuses).length === 0"
                    :variant="savedConnections.length > 0 ? 'success' : 'warning'"
                    pill
                  >
                    {{ savedConnections.length }}
                  </b-badge>
                </template>
              </div>
              <b-button
                size="sm"
                variant="secondary"
                @click="savedConnsCollapsed = !savedConnsCollapsed"
              >
                <b-icon-chevron-up v-if="savedConnsCollapsed" />
                <b-icon-chevron-down v-else />
              </b-button>
            </div>
          </b-card-header>
          <b-collapse v-model="savedConnsCollapsed">
            <b-card-body>
              <p class="text-muted">Connect to previously used DigiScript servers.</p>
              <b-list-group v-if="savedConnections.length > 0">
                <b-list-group-item
                  v-for="conn in savedConnections"
                  :key="conn.id"
                  class="d-flex justify-content-between align-items-center"
                >
                  <div class="text-left">
                    <div class="d-flex align-items-center mb-1">
                      <strong>{{ conn.nickname }}</strong>

                      <!-- Status Badge (always shown) -->
                      <b-badge :variant="getStatusVariant(conn.id)" class="ml-2" pill>
                        {{ getStatusText(conn.id) }}
                      </b-badge>
                    </div>

                    <div>
                      <small class="text-muted">{{ conn.url }}</small>
                    </div>

                    <!-- Version (always shown) -->
                    <div>
                      <small class="text-muted">
                        Version:
                        {{ serverStatuses[conn.id]?.serverVersion || 'Unknown' }}
                      </small>
                    </div>

                    <!-- Last seen (always shown) -->
                    <div>
                      <small class="text-muted">
                        Last seen:
                        {{
                          serverStatuses[conn.id]?.lastSeen
                            ? formatTimeAgo(serverStatuses[conn.id].lastSeen)
                            : 'Unknown'
                        }}
                      </small>
                    </div>

                    <!-- Last checked (always shown) -->
                    <div>
                      <small class="text-muted">
                        Last checked:
                        {{
                          serverStatuses[conn.id]?.lastChecked
                            ? formatTimeAgo(serverStatuses[conn.id].lastChecked)
                            : 'Unknown'
                        }}
                      </small>
                    </div>
                  </div>
                  <div>
                    <b-button
                      size="sm"
                      variant="primary"
                      class="mr-2"
                      :disabled="
                        isConnecting ||
                        (serverStatuses[conn.id] && !serverStatuses[conn.id].available)
                      "
                      @click="connectToServer(conn)"
                    >
                      Connect
                    </b-button>
                    <b-button size="sm" variant="danger" @click="confirmDeleteConnection(conn)">
                      Delete
                    </b-button>
                  </div>
                </b-list-group-item>
              </b-list-group>
              <b-alert v-else variant="warning" show> No saved connections. </b-alert>

              <!-- Add Server Button -->
              <div class="d-flex align-items-center mb-3">
                <b-button v-b-modal.add-server-modal variant="success" size="sm">
                  <b-icon-plus class="mr-1" /> Add New Server
                </b-button>
              </div>
            </b-card-body>
          </b-collapse>
        </b-card>
      </b-col>
    </b-row>

    <!-- Discovery Section -->
    <b-row style="margin-top: 0.25rem">
      <b-col>
        <b-card no-body class="mb-3">
          <b-card-header header-tag="header" class="p-3">
            <div class="d-flex justify-content-between align-items-center">
              <div class="d-flex align-items-center">
                <h6 class="mb-0 mr-2">Discover Servers</h6>
                <b-badge
                  :variant="discoveredServers.length > 0 ? 'success' : 'warning'"
                  class="mr-2"
                  pill
                >
                  {{ discoveredServers.length }}
                </b-badge>
                <template v-if="!discoverCollapsed">
                  <b-icon-arrow-clockwise
                    :variant="isDiscovering ? 'info' : 'success'"
                    :animation="isDiscovering ? 'spin' : ''"
                  />
                </template>
              </div>
              <b-button
                size="sm"
                variant="secondary"
                @click="discoverCollapsed = !discoverCollapsed"
              >
                <b-icon-chevron-up v-if="discoverCollapsed" />
                <b-icon-chevron-down v-else />
              </b-button>
            </div>
          </b-card-header>
          <b-collapse v-model="discoverCollapsed">
            <b-card-body>
              <p class="text-muted">
                Automatically discovering DigiScript servers on your local network...
              </p>
              <!-- Discovery Results -->
              <b-list-group v-if="discoveredServers.length > 0">
                <b-list-group-item
                  v-for="(server, index) in discoveredServers"
                  :key="index"
                  class="d-flex justify-content-between align-items-center"
                >
                  <div>
                    <strong>{{ server.name }}</strong>
                    <br />
                    <small class="text-muted">{{ server.url }}</small>
                    <br />
                    <small v-if="server.compatible" class="text-success">
                      ✓ Compatible (v{{ server.serverVersion }})
                    </small>
                    <small v-else-if="server.serverVersion" class="text-danger">
                      ✗ Incompatible (Server: v{{ server.serverVersion }}, Client: v{{
                        clientVersion
                      }})
                    </small>
                    <small v-else-if="server.versionError" class="text-warning">
                      {{ server.versionError }}
                    </small>
                  </div>
                  <div>
                    <b-button
                      size="sm"
                      variant="primary"
                      :disabled="!server.compatible || isConnecting"
                      @click="addDiscoveredServer(server)"
                    >
                      Add & Connect
                    </b-button>
                  </div>
                </b-list-group-item>
              </b-list-group>

              <!-- No servers found message -->
              <b-alert
                v-if="discoveryCompleted && discoveredServers.length === 0"
                show
                variant="warning"
              >
                No servers found on the local network.
              </b-alert>

              <!-- Status Indicator -->
              <div class="d-flex align-items-center mb-3">
                <b-icon-arrow-clockwise
                  class="mr-2"
                  :variant="isDiscovering ? 'info' : 'success'"
                  :animation="isDiscovering ? 'spin' : ''"
                />
                <span class="text-muted small">
                  <template v-if="isDiscovering"> Discovering... </template>
                  <template v-else-if="lastDiscoveryTime">
                    Last updated: {{ lastDiscoveryTimeFormatted }}
                  </template>
                  <template v-else> Starting discovery... </template>
                </span>
              </div>
            </b-card-body>
          </b-collapse>
        </b-card>
      </b-col>
    </b-row>

    <!-- Add Server Modal -->
    <b-modal
      id="add-server-modal"
      ref="add-server-modal"
      title="Add Server Manually"
      @hidden="resetManualForm"
    >
      <b-form @submit.prevent="addManualConnection">
        <b-form-group label="Nickname" label-for="nickname-input">
          <b-form-input
            id="nickname-input"
            v-model="$v.manualForm.nickname.$model"
            :state="validateState('nickname')"
            placeholder="e.g., Production Server"
          />
          <b-form-invalid-feedback> Nickname is required. </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group label="Server URL" label-for="url-input">
          <b-form-input
            id="url-input"
            v-model="$v.manualForm.url.$model"
            :state="validateState('url')"
            placeholder="e.g., http://192.168.1.100:8080"
          />
          <b-form-invalid-feedback>
            Valid URL is required (e.g., http://192.168.1.100:8080).
          </b-form-invalid-feedback>
        </b-form-group>

        <b-form-group>
          <b-form-checkbox v-model="manualForm.sslEnabled"> Use SSL (HTTPS) </b-form-checkbox>
        </b-form-group>

        <b-button
          type="button"
          variant="outline-secondary"
          class="mr-2"
          :disabled="isTestingConnection || $v.manualForm.$invalid"
          @click="testManualConnection"
        >
          <b-spinner v-if="isTestingConnection" small class="mr-2" />
          Test Connection
        </b-button>

        <!-- Test Result -->
        <b-alert
          v-if="testResult"
          :variant="testResult.variant"
          show
          dismissible
          class="mt-3"
          @dismissed="testResult = null"
        >
          {{ testResult.message }}
        </b-alert>
      </b-form>

      <template #modal-footer="{ cancel }">
        <b-button variant="secondary" @click="cancel()"> Cancel </b-button>
        <b-button
          variant="outline-success"
          :disabled="$v.manualForm.$invalid"
          @click="addServerOnly"
        >
          Add Only
        </b-button>
        <b-button
          variant="success"
          :disabled="$v.manualForm.$invalid || isConnecting"
          @click="addAndConnect"
        >
          <b-spinner v-if="isConnecting" small class="mr-2" />
          Add & Connect
        </b-button>
      </template>
    </b-modal>

    <!-- Delete Confirmation Modal -->
    <b-modal
      id="delete-modal"
      v-model="showDeleteModal"
      title="Delete Connection"
      @ok="deleteConnection"
    >
      <p>Are you sure you want to delete this connection?</p>
      <p>
        <strong>{{ connectionToDelete?.nickname }}</strong> ({{ connectionToDelete?.url }})
      </p>
    </b-modal>
  </b-container>
</template>

<script lang="ts">
import { defineComponent } from 'vue';
import { required } from 'vuelidate/lib/validators';
import { isElectron } from '@/js/platform';

interface SavedConnection {
  id: string;
  nickname: string;
  url: string;
  sslEnabled: boolean;
}

interface ServerStatus {
  available: boolean;
  compatible: boolean;
  serverVersion: string | null;
  lastSeen: number | null;
  lastChecked: number;
}

interface DiscoveredServer {
  name: string;
  url: string;
  compatible: boolean;
  serverVersion?: string;
  versionError?: string;
}

interface TestResult {
  variant: string;
  message: string;
}

const validUrl = (value: string): boolean => {
  if (!value) return false;
  try {
    const url = new URL(value.startsWith('http') ? value : `http://${value}`);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
};

export default defineComponent({
  name: 'ServerSelector',
  data() {
    return {
      savedConnections: [] as SavedConnection[],
      discoveredServers: [] as DiscoveredServer[],
      isDiscovering: false,
      discoveryCompleted: false,
      isTestingConnection: false,
      isConnecting: false,
      testResult: null as TestResult | null,
      clientVersion: null as string | null,
      manualForm: {
        nickname: '',
        url: '',
        sslEnabled: false,
      },
      showDeleteModal: false,
      connectionToDelete: null as SavedConnection | null,
      savedConnsCollapsed: true,
      discoverCollapsed: false,
      discoveryInterval: null as ReturnType<typeof setInterval> | null,
      lastDiscoveryTime: null as number | null,
      autoDiscoveryEnabled: true,
      currentTime: Date.now(),
      timeUpdateInterval: null as ReturnType<typeof setInterval> | null,
      serverStatusPollingInterval: null as ReturnType<typeof setInterval> | null,
      serverStatuses: {} as Record<string, ServerStatus>,
      isCheckingServers: false,
    };
  },
  computed: {
    secondsSinceLastDiscovery(): number | null {
      if (!this.lastDiscoveryTime) return null;
      return Math.floor((this.currentTime - this.lastDiscoveryTime) / 1000);
    },
    lastDiscoveryTimeFormatted(): string {
      if (!this.lastDiscoveryTime) return 'Never';
      const seconds = this.secondsSinceLastDiscovery!;
      if (seconds < 60) return `${seconds} seconds ago`;
      if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
      return this.formatDate(this.lastDiscoveryTime);
    },
    availableServersCount(): number {
      return this.savedConnections.filter((conn) => {
        const status = this.serverStatuses[conn.id];
        return status?.available && status?.compatible;
      }).length;
    },
    incompatibleServersCount(): number {
      return this.savedConnections.filter((conn) => {
        const status = this.serverStatuses[conn.id];
        return status?.available && !status?.compatible;
      }).length;
    },
    unavailableServersCount(): number {
      return this.savedConnections.filter((conn) => {
        const status = this.serverStatuses[conn.id];
        return status && !status.available;
      }).length;
    },
  },
  validations: {
    manualForm: {
      nickname: { required },
      url: { required, validUrl },
    },
  },
  async mounted(): Promise<void> {
    if (!isElectron()) {
      this.$router.push('/');
      return;
    }

    this.clientVersion = await (window as any).electronAPI.getAppVersion();
    await this.loadConnections();

    this.timeUpdateInterval = setInterval(() => {
      this.currentTime = Date.now();
    }, 1000);

    this.startAutoDiscovery();
    this.startServerStatusPolling();
  },
  beforeDestroy(): void {
    this.stopAutoDiscovery();
    this.stopServerStatusPolling();
    if (this.timeUpdateInterval) {
      clearInterval(this.timeUpdateInterval);
      this.timeUpdateInterval = null;
    }
  },
  methods: {
    validateState(name: string): boolean | null {
      const { $dirty, $error } = (this as any).$v.manualForm[name];
      return $dirty ? !$error : null;
    },
    async loadConnections(): Promise<void> {
      try {
        this.savedConnections = await (window as any).electronAPI.getAllConnections();
      } catch (error: any) {
        (this as any).$toast.error(`Failed to load connections: ${error.message}`);
      }
    },
    async discoverServers(): Promise<void> {
      if (this.isDiscovering || !this.autoDiscoveryEnabled) {
        return;
      }
      this.isDiscovering = true;
      try {
        this.discoveredServers = await (window as any).electronAPI.discoverServersWithVersionCheck(
          5000
        );
        this.discoveryCompleted = true;
        this.lastDiscoveryTime = Date.now();
      } catch (error: any) {
        console.warn('[Auto-Discovery] Failed:', error.message);
      } finally {
        this.isDiscovering = false;
      }
    },
    async checkServerStatus(connection: SavedConnection): Promise<ServerStatus> {
      try {
        const result = await (window as any).electronAPI.checkVersion(connection.url);
        if (result.error || !result.serverVersion) {
          return {
            available: false,
            compatible: false,
            serverVersion: null,
            lastSeen: this.serverStatuses[connection.id]?.lastSeen || null,
            lastChecked: Date.now(),
          };
        }
        return {
          available: true,
          compatible: result.compatible,
          serverVersion: result.serverVersion,
          lastSeen: Date.now(),
          lastChecked: Date.now(),
        };
      } catch {
        return {
          available: false,
          compatible: false,
          serverVersion: null,
          lastSeen: this.serverStatuses[connection.id]?.lastSeen || null,
          lastChecked: Date.now(),
        };
      }
    },
    async checkAllServerStatuses(): Promise<void> {
      if (this.isCheckingServers || this.savedConnections.length === 0) {
        return;
      }
      this.isCheckingServers = true;
      try {
        const statusChecks = this.savedConnections.map(async (conn) => {
          const status = await this.checkServerStatus(conn);
          return { id: conn.id, status };
        });
        const results = await Promise.all(statusChecks);
        results.forEach(({ id, status }) => {
          this.$set(this.serverStatuses, id, status);
        });
      } catch (error: any) {
        console.warn('[Server Status] Failed to check servers:', error.message);
      } finally {
        this.isCheckingServers = false;
      }
    },
    async testConnection(url: string): Promise<void> {
      this.isTestingConnection = true;
      this.testResult = null;
      try {
        const result = await (window as any).electronAPI.checkVersion(url);
        if (result.compatible) {
          this.testResult = {
            variant: 'success',
            message: `✓ Connection successful! Server version: ${result.serverVersion}`,
          };
        } else {
          this.testResult = {
            variant: 'danger',
            message: result.error || 'Version mismatch',
          };
        }
      } catch (error: any) {
        this.testResult = {
          variant: 'danger',
          message: `Connection failed: ${error.message}`,
        };
      } finally {
        this.isTestingConnection = false;
      }
    },
    async testManualConnection(): Promise<void> {
      const url = this.normalizeUrl(this.manualForm.url);
      await this.testConnection(url);
    },
    async connectToServer(connection: SavedConnection): Promise<void> {
      this.isConnecting = true;
      try {
        const versionCheck = await (window as any).electronAPI.checkVersion(connection.url);
        if (!versionCheck.compatible) {
          (this as any).$toast.error(versionCheck.error || 'Server version incompatible');
          return;
        }
        await (window as any).electronAPI.setActiveConnection(connection.id);
        (this as any).$toast.success(`Connected to ${connection.nickname}`);
        if ((this.$router as any).mode === 'history') {
          await this.$router.push('/');
        } else {
          window.location.hash = '/';
        }
        window.location.reload();
      } catch (error: any) {
        (this as any).$toast.error(`Connection failed: ${error.message}`);
      } finally {
        this.isConnecting = false;
      }
    },
    async addDiscoveredServer(server: DiscoveredServer): Promise<void> {
      this.isConnecting = true;
      try {
        const newConnection = await (window as any).electronAPI.addConnection({
          nickname: server.name,
          url: server.url,
          sslEnabled: server.url.startsWith('https'),
        });
        await (window as any).electronAPI.setActiveConnection(newConnection.id);
        (this as any).$toast.success(`Connected to ${server.name}`);
        if ((this.$router as any).mode === 'history') {
          await this.$router.push('/');
        } else {
          window.location.hash = '/';
        }
        window.location.reload();
      } catch (error: any) {
        (this as any).$toast.error(`Failed to add server: ${error.message}`);
      } finally {
        this.isConnecting = false;
      }
    },
    async addServerOnly(): Promise<void> {
      (this as any).$v.manualForm.$touch();
      if ((this as any).$v.manualForm.$invalid) {
        return;
      }
      try {
        const url = this.normalizeUrl(this.manualForm.url);
        const versionCheck = await (window as any).electronAPI.checkVersion(url);
        if (!versionCheck.compatible) {
          const proceed = await (this as any).$bvModal.msgBoxConfirm(
            `Server version (${versionCheck.serverVersion}) does not match client version. Add anyway?`,
            {
              title: 'Version Mismatch',
              okVariant: 'warning',
              okTitle: 'Add Anyway',
              cancelTitle: 'Cancel',
            }
          );
          if (!proceed) {
            return;
          }
        }
        await (window as any).electronAPI.addConnection({
          nickname: this.manualForm.nickname,
          url,
          sslEnabled: this.manualForm.sslEnabled,
        });
        (this as any).$toast.success(`Saved ${this.manualForm.nickname}`);
        await this.loadConnections();
        (this as any).$bvModal.hide('add-server-modal');
        await this.checkAllServerStatuses();
      } catch (error: any) {
        (this as any).$toast.error(`Failed to add server: ${error.message}`);
      }
    },
    async addAndConnect(): Promise<void> {
      (this as any).$v.manualForm.$touch();
      if ((this as any).$v.manualForm.$invalid) {
        return;
      }
      this.isConnecting = true;
      try {
        const url = this.normalizeUrl(this.manualForm.url);
        const versionCheck = await (window as any).electronAPI.checkVersion(url);
        if (!versionCheck.compatible) {
          (this as any).$toast.error(versionCheck.error || 'Server version incompatible');
          return;
        }
        const newConnection = await (window as any).electronAPI.addConnection({
          nickname: this.manualForm.nickname,
          url,
          sslEnabled: this.manualForm.sslEnabled,
        });
        await (window as any).electronAPI.setActiveConnection(newConnection.id);
        (this as any).$toast.success(`Connected to ${this.manualForm.nickname}`);
        if ((this.$router as any).mode === 'history') {
          await this.$router.push('/');
        } else {
          window.location.hash = '/';
        }
        window.location.reload();
      } catch (error: any) {
        (this as any).$toast.error(`Failed to add connection: ${error.message}`);
      } finally {
        this.isConnecting = false;
      }
    },
    confirmDeleteConnection(connection: SavedConnection): void {
      this.connectionToDelete = connection;
      this.showDeleteModal = true;
    },
    async deleteConnection(): Promise<void> {
      if (!this.connectionToDelete) return;
      try {
        await (window as any).electronAPI.deleteConnection(this.connectionToDelete.id);
        (this as any).$toast.success(`Deleted ${this.connectionToDelete.nickname}`);
        await this.loadConnections();
      } catch (error: any) {
        (this as any).$toast.error(`Failed to delete connection: ${error.message}`);
      } finally {
        this.connectionToDelete = null;
      }
    },
    normalizeUrl(url: string): string {
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        return this.manualForm.sslEnabled ? `https://${url}` : `http://${url}`;
      }
      return url;
    },
    formatDate(timestamp: number | null): string {
      if (!timestamp) return 'Never';
      return new Date(timestamp).toLocaleString();
    },
    formatTimeAgo(timestamp: number | null): string {
      if (!timestamp) return 'Never';
      const seconds = Math.floor((this.currentTime - timestamp) / 1000);
      if (seconds < 10) return 'Just now';
      if (seconds < 60) return `${seconds} seconds ago`;
      if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
      if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
      return `${Math.floor(seconds / 86400)} days ago`;
    },
    getStatusVariant(connectionId: string): string {
      const status = this.serverStatuses[connectionId];
      if (!status) return 'secondary';
      if (!status.available) return 'danger';
      if (!status.compatible) return 'warning';
      return 'success';
    },
    getStatusText(connectionId: string): string {
      const status = this.serverStatuses[connectionId];
      if (!status) return 'Checking...';
      if (!status.available) return 'Unavailable';
      if (!status.compatible) return 'Version Mismatch';
      return 'Available';
    },
    resetManualForm(): void {
      this.manualForm.nickname = '';
      this.manualForm.url = '';
      this.manualForm.sslEnabled = false;
      this.testResult = null;
      (this as any).$v.manualForm.$reset();
    },
    startAutoDiscovery(): void {
      this.discoverServers();
      this.discoveryInterval = setInterval(() => {
        this.discoverServers();
      }, 15000);
    },
    stopAutoDiscovery(): void {
      if (this.discoveryInterval) {
        clearInterval(this.discoveryInterval);
        this.discoveryInterval = null;
      }
    },
    startServerStatusPolling(): void {
      this.checkAllServerStatuses();
      this.serverStatusPollingInterval = setInterval(() => {
        this.checkAllServerStatuses();
      }, 30000);
    },
    stopServerStatusPolling(): void {
      if (this.serverStatusPollingInterval) {
        clearInterval(this.serverStatusPollingInterval);
        this.serverStatusPollingInterval = null;
      }
    },
  },
});
</script>

<style scoped>
.list-group-item {
  margin-bottom: 0.5rem;
}
</style>
