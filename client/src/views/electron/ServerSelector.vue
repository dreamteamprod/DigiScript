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
    <b-row v-if="savedConnections.length > 0" style="margin-top: 2rem">
      <b-col>
        <h5>Saved Connections</h5>
        <b-list-group>
          <b-list-group-item
            v-for="conn in savedConnections"
            :key="conn.id"
            class="d-flex justify-content-between align-items-center"
          >
            <div>
              <strong>{{ conn.nickname }}</strong>
              <br />
              <small class="text-muted">{{ conn.url }}</small>
              <br />
              <small v-if="conn.lastConnected" class="text-muted">
                Last connected: {{ formatDate(conn.lastConnected) }}
              </small>
            </div>
            <div>
              <b-button
                size="sm"
                variant="primary"
                class="mr-2"
                :disabled="isConnecting"
                @click="connectToServer(conn)"
              >
                Connect
              </b-button>
              <b-button
                size="sm"
                variant="outline-secondary"
                class="mr-2"
                :disabled="isTestingConnection"
                @click="testConnection(conn.url)"
              >
                Test
              </b-button>
              <b-button size="sm" variant="danger" @click="confirmDeleteConnection(conn)">
                Delete
              </b-button>
            </div>
          </b-list-group-item>
        </b-list-group>
      </b-col>
    </b-row>

    <!-- Discovery Section -->
    <b-row style="margin-top: 2rem">
      <b-col>
        <h5>Discover Servers</h5>
        <p class="text-muted">Find DigiScript servers on your local network.</p>
        <b-button variant="info" :disabled="isDiscovering" @click="discoverServers">
          <b-spinner v-if="isDiscovering" small class="mr-2" />
          {{ isDiscovering ? 'Discovering...' : 'Discover Servers' }}
        </b-button>

        <!-- Discovery Results -->
        <b-list-group v-if="discoveredServers.length > 0" class="mt-3">
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
                ✗ Incompatible (Server: v{{ server.serverVersion }}, Client: v{{ clientVersion }})
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
          variant="info"
          class="mt-3"
        >
          No servers found on the local network. Try adding a server manually below.
        </b-alert>
      </b-col>
    </b-row>

    <!-- Manual Entry Form -->
    <b-row style="margin-top: 2rem">
      <b-col>
        <h5>Add Server Manually</h5>
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

          <b-button
            type="submit"
            variant="success"
            :disabled="$v.manualForm.$invalid || isConnecting"
          >
            <b-spinner v-if="isConnecting" small class="mr-2" />
            Add & Connect
          </b-button>
        </b-form>

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
      </b-col>
    </b-row>

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

<script>
import { required } from 'vuelidate/lib/validators';
import { isElectron } from '@/js/platform';

// Custom URL validator
const validUrl = (value) => {
  if (!value) return false;
  try {
    const url = new URL(value.startsWith('http') ? value : `http://${value}`);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
};

export default {
  name: 'ServerSelector',
  data() {
    return {
      savedConnections: [],
      discoveredServers: [],
      isDiscovering: false,
      discoveryCompleted: false,
      isTestingConnection: false,
      isConnecting: false,
      testResult: null,
      clientVersion: null,
      manualForm: {
        nickname: '',
        url: '',
        sslEnabled: false,
      },
      showDeleteModal: false,
      connectionToDelete: null,
    };
  },
  validations: {
    manualForm: {
      nickname: { required },
      url: { required, validUrl },
    },
  },
  async mounted() {
    // Redirect to home if not in Electron
    if (!isElectron()) {
      this.$router.push('/');
      return;
    }

    // Load client version
    this.clientVersion = await window.electronAPI.getAppVersion();

    // Load saved connections
    await this.loadConnections();
  },
  methods: {
    /**
     * Validate form field state for Vuelidate
     */
    validateState(name) {
      const { $dirty, $error } = this.$v.manualForm[name];
      return $dirty ? !$error : null;
    },

    /**
     * Load all saved connections from Electron store
     */
    async loadConnections() {
      try {
        this.savedConnections = await window.electronAPI.getAllConnections();
      } catch (error) {
        this.$toast.error(`Failed to load connections: ${error.message}`);
      }
    },

    /**
     * Discover servers on local network using mDNS
     */
    async discoverServers() {
      this.isDiscovering = true;
      this.discoveredServers = [];
      this.discoveryCompleted = false;

      try {
        // Discover servers with version checking
        this.discoveredServers = await window.electronAPI.discoverServersWithVersionCheck(5000);
        this.discoveryCompleted = true;

        if (this.discoveredServers.length === 0) {
          this.$toast.info('No servers found on local network');
        } else {
          this.$toast.success(`Found ${this.discoveredServers.length} server(s)`);
        }
      } catch (error) {
        this.$toast.error(`Discovery failed: ${error.message}`);
      } finally {
        this.isDiscovering = false;
      }
    },

    /**
     * Test connection to a server URL
     */
    async testConnection(url) {
      this.isTestingConnection = true;
      this.testResult = null;

      try {
        const result = await window.electronAPI.checkVersion(url);

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
      } catch (error) {
        this.testResult = {
          variant: 'danger',
          message: `Connection failed: ${error.message}`,
        };
      } finally {
        this.isTestingConnection = false;
      }
    },

    /**
     * Test manual connection entry
     */
    async testManualConnection() {
      const url = this.normalizeUrl(this.manualForm.url);
      await this.testConnection(url);
    },

    /**
     * Connect to a saved server
     */
    async connectToServer(connection) {
      this.isConnecting = true;

      try {
        // Verify version compatibility first
        const versionCheck = await window.electronAPI.checkVersion(connection.url);

        if (!versionCheck.compatible) {
          this.$toast.error(versionCheck.error || 'Server version incompatible');
          return;
        }

        // Set as active connection
        await window.electronAPI.setActiveConnection(connection.id);

        this.$toast.success(`Connected to ${connection.nickname}`);

        // Reload the page to reinitialize WebSocket with new connection
        window.location.href = '/';
      } catch (error) {
        this.$toast.error(`Connection failed: ${error.message}`);
      } finally {
        this.isConnecting = false;
      }
    },

    /**
     * Add discovered server as saved connection and connect
     */
    async addDiscoveredServer(server) {
      this.isConnecting = true;

      try {
        // Add connection
        const newConnection = await window.electronAPI.addConnection({
          nickname: server.name,
          url: server.url,
          sslEnabled: server.url.startsWith('https'),
        });

        // Set as active and connect
        await window.electronAPI.setActiveConnection(newConnection.id);

        this.$toast.success(`Connected to ${server.name}`);

        // Reload the page to reinitialize WebSocket with new connection
        window.location.href = '/';
      } catch (error) {
        this.$toast.error(`Failed to add server: ${error.message}`);
      } finally {
        this.isConnecting = false;
      }
    },

    /**
     * Add manual connection and connect
     */
    async addManualConnection() {
      this.$v.manualForm.$touch();
      if (this.$v.manualForm.$invalid) {
        return;
      }

      this.isConnecting = true;

      try {
        const url = this.normalizeUrl(this.manualForm.url);

        // Verify version compatibility first
        const versionCheck = await window.electronAPI.checkVersion(url);

        if (!versionCheck.compatible) {
          this.$toast.error(versionCheck.error || 'Server version incompatible');
          return;
        }

        // Add connection
        const newConnection = await window.electronAPI.addConnection({
          nickname: this.manualForm.nickname,
          url,
          sslEnabled: this.manualForm.sslEnabled,
        });

        // Set as active and connect
        await window.electronAPI.setActiveConnection(newConnection.id);

        this.$toast.success(`Connected to ${this.manualForm.nickname}`);

        // Reload the page to reinitialize WebSocket with new connection
        window.location.href = '/';
      } catch (error) {
        this.$toast.error(`Failed to add connection: ${error.message}`);
      } finally {
        this.isConnecting = false;
      }
    },

    /**
     * Show delete confirmation modal
     */
    confirmDeleteConnection(connection) {
      this.connectionToDelete = connection;
      this.showDeleteModal = true;
    },

    /**
     * Delete a saved connection
     */
    async deleteConnection() {
      if (!this.connectionToDelete) return;

      try {
        await window.electronAPI.deleteConnection(this.connectionToDelete.id);
        this.$toast.success(`Deleted ${this.connectionToDelete.nickname}`);

        // Reload connections
        await this.loadConnections();
      } catch (error) {
        this.$toast.error(`Failed to delete connection: ${error.message}`);
      } finally {
        this.connectionToDelete = null;
      }
    },

    /**
     * Normalize URL (add protocol if missing)
     */
    normalizeUrl(url) {
      if (!url.startsWith('http://') && !url.startsWith('https://')) {
        return this.manualForm.sslEnabled ? `https://${url}` : `http://${url}`;
      }
      return url;
    },

    /**
     * Format timestamp for display
     */
    formatDate(timestamp) {
      if (!timestamp) return 'Never';
      const date = new Date(timestamp);
      return date.toLocaleString();
    },
  },
};
</script>

<style scoped>
.list-group-item {
  margin-bottom: 0.5rem;
}
</style>
