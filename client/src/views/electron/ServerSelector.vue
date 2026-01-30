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
    // Invalid URL syntax - return false for validation
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
      savedConnsCollapsed: true,
      discoverCollapsed: false,
      discoveryInterval: null,
      lastDiscoveryTime: null,
      autoDiscoveryEnabled: true,
      currentTime: Date.now(),
      timeUpdateInterval: null,
      serverStatusPollingInterval: null,
      serverStatuses: {}, // Map of connectionId -> status object
      isCheckingServers: false,
    };
  },
  computed: {
    /**
     * Calculate seconds since last discovery
     * @returns {number|null} Seconds elapsed or null if never run
     */
    secondsSinceLastDiscovery() {
      if (!this.lastDiscoveryTime) return null;
      return Math.floor((this.currentTime - this.lastDiscoveryTime) / 1000);
    },

    /**
     * Format last update time for display
     * @returns {string} Human-readable time string
     */
    lastDiscoveryTimeFormatted() {
      if (!this.lastDiscoveryTime) return 'Never';
      const seconds = this.secondsSinceLastDiscovery;

      if (seconds < 60) return `${seconds} seconds ago`;
      if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
      return this.formatDate(this.lastDiscoveryTime);
    },

    /**
     * Count of available servers with compatible versions
     * @returns {number} Number of available and compatible servers
     */
    availableServersCount() {
      return this.savedConnections.filter((conn) => {
        const status = this.serverStatuses[conn.id];
        return status?.available && status?.compatible;
      }).length;
    },

    /**
     * Count of available servers with incompatible versions
     * @returns {number} Number of available but incompatible servers
     */
    incompatibleServersCount() {
      return this.savedConnections.filter((conn) => {
        const status = this.serverStatuses[conn.id];
        return status?.available && !status?.compatible;
      }).length;
    },

    /**
     * Count of unavailable servers
     * @returns {number} Number of unavailable servers
     */
    unavailableServersCount() {
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

    // Start time update interval for reactive timestamp
    this.timeUpdateInterval = setInterval(() => {
      this.currentTime = Date.now();
    }, 1000);

    // Start auto-discovery
    this.startAutoDiscovery();

    // Start server status polling
    this.startServerStatusPolling();
  },
  beforeDestroy() {
    // Clean up auto-discovery interval
    this.stopAutoDiscovery();

    // Clean up server status polling
    this.stopServerStatusPolling();

    // Clean up time update interval
    if (this.timeUpdateInterval) {
      clearInterval(this.timeUpdateInterval);
      this.timeUpdateInterval = null;
    }
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
     * Runs automatically every 15 seconds
     */
    async discoverServers() {
      // Skip if already discovering or disabled
      if (this.isDiscovering || !this.autoDiscoveryEnabled) {
        return;
      }

      this.isDiscovering = true;

      try {
        this.discoveredServers = await window.electronAPI.discoverServersWithVersionCheck(5000);
        this.discoveryCompleted = true;
        this.lastDiscoveryTime = Date.now();
      } catch (error) {
        // Silent failure - log only
        console.warn('[Auto-Discovery] Failed:', error.message);
      } finally {
        this.isDiscovering = false;
      }
    },

    /**
     * Check status of a single server
     * @param {Object} connection - Connection object
     * @returns {Object} Status object with availability, compatibility, version info
     */
    async checkServerStatus(connection) {
      try {
        const result = await window.electronAPI.checkVersion(connection.url);

        // If there's an error field or no serverVersion, the server is unreachable
        if (result.error || !result.serverVersion) {
          return {
            available: false,
            compatible: false,
            serverVersion: null,
            lastSeen: this.serverStatuses[connection.id]?.lastSeen || null,
            lastChecked: Date.now(),
          };
        }

        // Server is reachable, check compatibility
        return {
          available: true,
          compatible: result.compatible,
          serverVersion: result.serverVersion,
          lastSeen: Date.now(),
          lastChecked: Date.now(),
        };
      } catch (error) {
        // Exception thrown - server unavailable or check failed
        return {
          available: false,
          compatible: false,
          serverVersion: null,
          lastSeen: this.serverStatuses[connection.id]?.lastSeen || null,
          lastChecked: Date.now(),
        };
      }
    },

    /**
     * Check status of all saved servers
     * Runs in parallel using Promise.all()
     */
    async checkAllServerStatuses() {
      if (this.isCheckingServers || this.savedConnections.length === 0) {
        return;
      }

      this.isCheckingServers = true;

      try {
        // Check all servers in parallel
        const statusChecks = this.savedConnections.map(async (conn) => {
          const status = await this.checkServerStatus(conn);
          return { id: conn.id, status };
        });

        const results = await Promise.all(statusChecks);

        // Update statuses using $set for reactivity
        results.forEach(({ id, status }) => {
          this.$set(this.serverStatuses, id, status);
        });
      } catch (error) {
        console.warn('[Server Status] Failed to check servers:', error.message);
      } finally {
        this.isCheckingServers = false;
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

        // Force full page reload to reinitialize WebSocket
        // In history mode (dev), use router to navigate before reload
        // In hash mode (prod), set hash before reload
        if (this.$router.mode === 'history') {
          await this.$router.push('/');
        } else {
          window.location.hash = '/';
        }
        window.location.reload();
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

        // Force full page reload to reinitialize WebSocket
        // In history mode (dev), use router to navigate before reload
        // In hash mode (prod), set hash before reload
        if (this.$router.mode === 'history') {
          await this.$router.push('/');
        } else {
          window.location.hash = '/';
        }
        window.location.reload();
      } catch (error) {
        this.$toast.error(`Failed to add server: ${error.message}`);
      } finally {
        this.isConnecting = false;
      }
    },

    /**
     * Add server without connecting
     */
    async addServerOnly() {
      this.$v.manualForm.$touch();
      if (this.$v.manualForm.$invalid) {
        return;
      }

      try {
        const url = this.normalizeUrl(this.manualForm.url);

        // Verify version compatibility first
        const versionCheck = await window.electronAPI.checkVersion(url);

        if (!versionCheck.compatible) {
          // Show warning but allow adding anyway
          const proceed = await this.$bvModal.msgBoxConfirm(
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

        // Add connection (don't set as active)
        await window.electronAPI.addConnection({
          nickname: this.manualForm.nickname,
          url,
          sslEnabled: this.manualForm.sslEnabled,
        });

        this.$toast.success(`Saved ${this.manualForm.nickname}`);

        // Reload connections list
        await this.loadConnections();

        // Close modal
        this.$bvModal.hide('add-server-modal');

        // Trigger immediate status check for new server
        await this.checkAllServerStatuses();
      } catch (error) {
        this.$toast.error(`Failed to add server: ${error.message}`);
      }
    },

    /**
     * Add manual connection and connect immediately
     */
    async addAndConnect() {
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

        // Force full page reload to reinitialize WebSocket
        // In history mode (dev), use router to navigate before reload
        // In hash mode (prod), set hash before reload
        if (this.$router.mode === 'history') {
          await this.$router.push('/');
        } else {
          window.location.hash = '/';
        }
        window.location.reload();
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

    /**
     * Format timestamp as "time ago" string
     * @param {number} timestamp - Timestamp in milliseconds
     * @returns {string} Human-readable "time ago" string
     */
    formatTimeAgo(timestamp) {
      if (!timestamp) return 'Never';

      const seconds = Math.floor((this.currentTime - timestamp) / 1000);

      if (seconds < 10) return 'Just now';
      if (seconds < 60) return `${seconds} seconds ago`;
      if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
      if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
      return `${Math.floor(seconds / 86400)} days ago`;
    },

    /**
     * Get badge variant for connection status
     * @param {string} connectionId - Connection ID
     * @returns {string} Bootstrap variant (secondary=checking, danger=unavailable, warning=mismatch, success=available)
     */
    getStatusVariant(connectionId) {
      const status = this.serverStatuses[connectionId];

      // No status yet - still checking
      if (!status) return 'secondary';

      // Server unreachable
      if (!status.available) return 'danger';

      // Server reachable but wrong version
      if (!status.compatible) return 'warning';

      // Server reachable and compatible
      return 'success';
    },

    /**
     * Get status text for connection
     * @param {string} connectionId - Connection ID
     * @returns {string} Status text
     */
    getStatusText(connectionId) {
      const status = this.serverStatuses[connectionId];

      // No status yet - still checking
      if (!status) return 'Checking...';

      // Server unreachable
      if (!status.available) return 'Unavailable';

      // Server reachable but wrong version
      if (!status.compatible) return 'Version Mismatch';

      // Server reachable and compatible
      return 'Available';
    },

    /**
     * Reset manual form when modal is closed
     */
    resetManualForm() {
      this.manualForm.nickname = '';
      this.manualForm.url = '';
      this.manualForm.sslEnabled = false;
      this.testResult = null;
      this.$v.manualForm.$reset();
    },

    /**
     * Start auto-discovery interval
     */
    startAutoDiscovery() {
      // Run first discovery immediately
      this.discoverServers();

      // Set up recurring discovery every 15 seconds
      this.discoveryInterval = setInterval(() => {
        this.discoverServers();
      }, 15000);
    },

    /**
     * Stop auto-discovery interval
     */
    stopAutoDiscovery() {
      if (this.discoveryInterval) {
        clearInterval(this.discoveryInterval);
        this.discoveryInterval = null;
      }
    },

    /**
     * Start server status polling
     * Checks all saved servers every 30 seconds
     */
    startServerStatusPolling() {
      // Run first check immediately
      this.checkAllServerStatuses();

      // Set up recurring checks every 30 seconds
      this.serverStatusPollingInterval = setInterval(() => {
        this.checkAllServerStatuses();
      }, 30000);
    },

    /**
     * Stop server status polling
     */
    stopServerStatusPolling() {
      if (this.serverStatusPollingInterval) {
        clearInterval(this.serverStatusPollingInterval);
        this.serverStatusPollingInterval = null;
      }
    },
  },
};
</script>

<style scoped>
.list-group-item {
  margin-bottom: 0.5rem;
}
</style>
