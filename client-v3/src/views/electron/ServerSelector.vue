<template>
  <BContainer fluid class="mx-0">
    <BRow class="mt-3">
      <BCol>
        <h3>Connect to DigiScript Server</h3>
        <p class="text-muted">
          Select a saved connection, discover servers on your network, or add a new server manually.
        </p>
      </BCol>
    </BRow>

    <!-- Saved Connections -->
    <BRow class="mt-4">
      <BCol>
        <BCard no-body class="mb-3">
          <BCardHeader class="p-3">
            <div class="d-flex justify-content-between align-items-center">
              <div class="d-flex align-items-center">
                <h6 class="mb-0 me-2">Saved Connections</h6>
                <template v-if="!savedConnsCollapsed">
                  <BBadge v-if="availableServersCount > 0" variant="success" pill class="me-1">
                    {{ availableServersCount }}
                  </BBadge>
                  <BBadge v-if="incompatibleServersCount > 0" variant="warning" pill class="me-1">
                    {{ incompatibleServersCount }}
                  </BBadge>
                  <BBadge v-if="unavailableServersCount > 0" variant="danger" pill class="me-1">
                    {{ unavailableServersCount }}
                  </BBadge>
                  <BBadge
                    v-if="Object.keys(serverStatuses).length === 0"
                    :variant="savedConnections.length > 0 ? 'success' : 'warning'"
                    pill
                  >
                    {{ savedConnections.length }}
                  </BBadge>
                </template>
              </div>
              <BButton
                size="sm"
                variant="secondary"
                @click="savedConnsCollapsed = !savedConnsCollapsed"
              >
                <IMdiChevronUp v-if="savedConnsCollapsed" />
                <IMdiChevronDown v-else />
              </BButton>
            </div>
          </BCardHeader>
          <BCollapse :visible="!savedConnsCollapsed">
            <BCardBody>
              <p class="text-muted">Connect to previously used DigiScript servers.</p>
              <BListGroup v-if="savedConnections.length > 0">
                <BListGroupItem
                  v-for="conn in savedConnections"
                  :key="conn.id"
                  class="d-flex justify-content-between align-items-center"
                >
                  <div class="text-start">
                    <div class="d-flex align-items-center mb-1">
                      <strong>{{ conn.nickname }}</strong>
                      <BBadge :variant="getStatusVariant(conn.id)" class="ms-2" pill>
                        {{ getStatusText(conn.id) }}
                      </BBadge>
                    </div>
                    <div>
                      <small class="text-muted">{{ conn.url }}</small>
                    </div>
                    <div>
                      <small class="text-muted">
                        Version: {{ serverStatuses[conn.id]?.serverVersion || 'Unknown' }}
                      </small>
                    </div>
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
                    <BButton
                      size="sm"
                      variant="primary"
                      class="me-2"
                      :disabled="
                        isConnecting ||
                        (!!serverStatuses[conn.id] && !serverStatuses[conn.id].available)
                      "
                      @click="connectToServer(conn)"
                    >
                      Connect
                    </BButton>
                    <BButton size="sm" variant="danger" @click="confirmDeleteConnection(conn)">
                      Delete
                    </BButton>
                  </div>
                </BListGroupItem>
              </BListGroup>
              <BAlert v-else variant="warning" :model-value="true">No saved connections.</BAlert>

              <div class="d-flex align-items-center mt-3">
                <BButton variant="success" size="sm" @click="showAddModal = true">
                  <IMdiPlus class="me-1" /> Add New Server
                </BButton>
              </div>
            </BCardBody>
          </BCollapse>
        </BCard>
      </BCol>
    </BRow>

    <!-- Discover Servers -->
    <BRow style="margin-top: 0.25rem">
      <BCol>
        <BCard no-body class="mb-3">
          <BCardHeader class="p-3">
            <div class="d-flex justify-content-between align-items-center">
              <div class="d-flex align-items-center">
                <h6 class="mb-0 me-2">Discover Servers</h6>
                <BBadge
                  :variant="discoveredServers.length > 0 ? 'success' : 'warning'"
                  class="me-2"
                  pill
                >
                  {{ discoveredServers.length }}
                </BBadge>
                <template v-if="!discoverCollapsed">
                  <IMdiRefresh :class="isDiscovering ? 'spin text-info' : 'text-success'" />
                </template>
              </div>
              <BButton
                size="sm"
                variant="secondary"
                @click="discoverCollapsed = !discoverCollapsed"
              >
                <IMdiChevronUp v-if="discoverCollapsed" />
                <IMdiChevronDown v-else />
              </BButton>
            </div>
          </BCardHeader>
          <BCollapse :visible="!discoverCollapsed">
            <BCardBody>
              <p class="text-muted">
                Automatically discovering DigiScript servers on your local network...
              </p>
              <BListGroup v-if="discoveredServers.length > 0">
                <BListGroupItem
                  v-for="(server, index) in discoveredServers"
                  :key="index"
                  class="d-flex justify-content-between align-items-center"
                >
                  <div>
                    <strong>{{ server.name }}</strong
                    ><br />
                    <small class="text-muted">{{ server.url }}</small
                    ><br />
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
                    <BButton
                      size="sm"
                      variant="primary"
                      :disabled="!server.compatible || isConnecting"
                      @click="addDiscoveredServer(server)"
                    >
                      Add &amp; Connect
                    </BButton>
                  </div>
                </BListGroupItem>
              </BListGroup>

              <BAlert
                v-if="discoveryCompleted && discoveredServers.length === 0"
                variant="warning"
                :model-value="true"
              >
                No servers found on the local network.
              </BAlert>

              <div class="d-flex align-items-center mt-3">
                <IMdiRefresh
                  class="me-2"
                  :class="isDiscovering ? 'spin text-info' : 'text-success'"
                />
                <span class="text-muted small">
                  <template v-if="isDiscovering">Discovering...</template>
                  <template v-else-if="lastDiscoveryTime">
                    Last updated: {{ lastDiscoveryTimeFormatted }}
                  </template>
                  <template v-else>Starting discovery...</template>
                </span>
              </div>
            </BCardBody>
          </BCollapse>
        </BCard>
      </BCol>
    </BRow>

    <!-- Add Server Modal -->
    <BModal v-model="showAddModal" title="Add Server Manually" @hidden="resetManualForm">
      <BForm @submit.prevent>
        <BFormGroup label="Nickname" label-for="nickname-input">
          <BFormInput
            id="nickname-input"
            v-model="manualForm.nickname"
            :state="v$.nickname.$dirty ? !v$.nickname.$error : null"
            placeholder="e.g., Production Server"
            @blur="v$.nickname.$touch()"
          />
          <BFormInvalidFeedback>Nickname is required.</BFormInvalidFeedback>
        </BFormGroup>

        <BFormGroup label="Server URL" label-for="url-input">
          <BFormInput
            id="url-input"
            v-model="manualForm.url"
            :state="v$.url.$dirty ? !v$.url.$error : null"
            placeholder="e.g., http://192.168.1.100:8080"
            @blur="v$.url.$touch()"
          />
          <BFormInvalidFeedback>
            Valid URL is required (e.g., http://192.168.1.100:8080).
          </BFormInvalidFeedback>
        </BFormGroup>

        <BFormGroup>
          <BFormCheckbox v-model="manualForm.sslEnabled">Use SSL (HTTPS)</BFormCheckbox>
        </BFormGroup>

        <BButton
          type="button"
          variant="outline-secondary"
          class="me-2"
          :disabled="isTestingConnection || v$.$invalid"
          @click="testManualConnection"
        >
          <BSpinner v-if="isTestingConnection" small class="me-2" />
          Test Connection
        </BButton>

        <BAlert
          v-if="testResult"
          :variant="testResult.variant"
          :model-value="true"
          dismissible
          class="mt-3"
          @dismissed="testResult = null"
        >
          {{ testResult.message }}
        </BAlert>
      </BForm>

      <template #footer="{ cancel }">
        <BButton variant="secondary" @click="cancel()">Cancel</BButton>
        <BButton variant="outline-success" :disabled="v$.$invalid" @click="addServerOnly">
          Add Only
        </BButton>
        <BButton variant="success" :disabled="v$.$invalid || isConnecting" @click="addAndConnect">
          <BSpinner v-if="isConnecting" small class="me-2" />
          Add &amp; Connect
        </BButton>
      </template>
    </BModal>

    <!-- Delete Confirmation Modal -->
    <BModal v-model="showDeleteModal" title="Delete Connection" @ok="deleteConnection">
      <p>Are you sure you want to delete this connection?</p>
      <p>
        <strong>{{ connectionToDelete?.nickname }}</strong> ({{ connectionToDelete?.url }})
      </p>
    </BModal>
  </BContainer>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRouter } from 'vue-router';
import { useVuelidate } from '@vuelidate/core';
import { required } from '@vuelidate/validators';
import type {
  ElectronConnection,
  ElectronDiscoveredServer,
  ElectronVersionCheckResult,
} from '@/js/platform/electron';
import { toast } from '@/js/toast';
import { useConfirm } from '@/composables/useConfirm';

interface ServerStatus {
  available: boolean;
  compatible: boolean;
  serverVersion: string | null;
  lastSeen: number | null;
  lastChecked: number;
}

interface TestResult {
  variant: string;
  message: string;
}

const router = useRouter();
const { confirm } = useConfirm();

const savedConnections = ref<ElectronConnection[]>([]);
const serverStatuses = ref<Record<string, ServerStatus>>({});
const discoveredServers = ref<ElectronDiscoveredServer[]>([]);
const isDiscovering = ref(false);
const discoveryCompleted = ref(false);
const isTestingConnection = ref(false);
const isConnecting = ref(false);
const isCheckingServers = ref(false);
const testResult = ref<TestResult | null>(null);
const clientVersion = ref<string | null>(null);
const showDeleteModal = ref(false);
const connectionToDelete = ref<ElectronConnection | null>(null);
const savedConnsCollapsed = ref(true);
const discoverCollapsed = ref(false);
const lastDiscoveryTime = ref<number | null>(null);
const currentTime = ref(Date.now());
const showAddModal = ref(false);

const manualForm = ref({ nickname: '', url: '', sslEnabled: false });

const validUrl = (value: string): boolean => {
  if (!value) return false;
  try {
    const url = new URL(value.startsWith('http') ? value : `http://${value}`);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
};

const rules = { nickname: { required }, url: { required, validUrl } };
const v$ = useVuelidate(rules, manualForm);

const secondsSinceLastDiscovery = computed(() => {
  if (!lastDiscoveryTime.value) return null;
  return Math.floor((currentTime.value - lastDiscoveryTime.value) / 1000);
});

const lastDiscoveryTimeFormatted = computed(() => {
  if (!lastDiscoveryTime.value) return 'Never';
  const seconds = secondsSinceLastDiscovery.value!;
  if (seconds < 60) return `${seconds} seconds ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
  return formatDate(lastDiscoveryTime.value);
});

const availableServersCount = computed(
  () =>
    savedConnections.value.filter((c) => {
      const s = serverStatuses.value[c.id];
      return s?.available && s?.compatible;
    }).length
);

const incompatibleServersCount = computed(
  () =>
    savedConnections.value.filter((c) => {
      const s = serverStatuses.value[c.id];
      return s?.available && !s?.compatible;
    }).length
);

const unavailableServersCount = computed(
  () =>
    savedConnections.value.filter(
      (c) => serverStatuses.value[c.id] && !serverStatuses.value[c.id].available
    ).length
);

let discoveryInterval: ReturnType<typeof setInterval> | null = null;
let serverStatusPollingInterval: ReturnType<typeof setInterval> | null = null;
let timeUpdateInterval: ReturnType<typeof setInterval> | null = null;

onMounted(async () => {
  clientVersion.value = (await window.electronAPI?.getAppVersion?.()) ?? null;
  await loadConnections();
  timeUpdateInterval = setInterval(() => {
    currentTime.value = Date.now();
  }, 1000);
  startAutoDiscovery();
  startServerStatusPolling();
});

onBeforeUnmount(() => {
  stopAutoDiscovery();
  stopServerStatusPolling();
  if (timeUpdateInterval) clearInterval(timeUpdateInterval);
});

async function loadConnections(): Promise<void> {
  try {
    savedConnections.value = (await window.electronAPI?.getAllConnections?.()) ?? [];
  } catch (error: unknown) {
    toast.error(`Failed to load connections: ${(error as Error).message}`);
  }
}

async function discoverServers(): Promise<void> {
  if (isDiscovering.value) return;
  isDiscovering.value = true;
  try {
    discoveredServers.value =
      (await window.electronAPI?.discoverServersWithVersionCheck?.(5000)) ?? [];
    discoveryCompleted.value = true;
    lastDiscoveryTime.value = Date.now();
  } catch (error: unknown) {
    console.warn('[Auto-Discovery] Failed:', (error as Error).message);
  } finally {
    isDiscovering.value = false;
  }
}

async function checkServerStatus(connection: ElectronConnection): Promise<ServerStatus> {
  try {
    const result = (await window.electronAPI?.checkVersion?.(connection.url)) as
      | ElectronVersionCheckResult
      | undefined;
    if (!result || result.error || !result.serverVersion) {
      return {
        available: false,
        compatible: false,
        serverVersion: null,
        lastSeen: serverStatuses.value[connection.id]?.lastSeen ?? null,
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
      lastSeen: serverStatuses.value[connection.id]?.lastSeen ?? null,
      lastChecked: Date.now(),
    };
  }
}

async function checkAllServerStatuses(): Promise<void> {
  if (isCheckingServers.value || savedConnections.value.length === 0) return;
  isCheckingServers.value = true;
  try {
    const results = await Promise.all(
      savedConnections.value.map(async (conn) => ({
        id: conn.id,
        status: await checkServerStatus(conn),
      }))
    );
    results.forEach(({ id, status }) => {
      serverStatuses.value[id] = status;
    });
  } catch (error: unknown) {
    console.warn('[Server Status] Failed:', (error as Error).message);
  } finally {
    isCheckingServers.value = false;
  }
}

async function connectToServer(connection: ElectronConnection): Promise<void> {
  isConnecting.value = true;
  try {
    const versionCheck = await window.electronAPI?.checkVersion?.(connection.url);
    if (!versionCheck?.compatible) {
      toast.error(versionCheck?.error ?? 'Server version incompatible');
      return;
    }
    await window.electronAPI?.setActiveConnection?.(connection.id);
    toast.success(`Connected to ${connection.nickname}`);
    await router.push('/');
    window.location.reload();
  } catch (error: unknown) {
    toast.error(`Connection failed: ${(error as Error).message}`);
  } finally {
    isConnecting.value = false;
  }
}

async function addDiscoveredServer(server: ElectronDiscoveredServer): Promise<void> {
  isConnecting.value = true;
  try {
    const newConn = await window.electronAPI?.addConnection?.({
      nickname: server.name,
      url: server.url,
      sslEnabled: server.url.startsWith('https'),
    });
    if (!newConn) throw new Error('Failed to add connection');
    await window.electronAPI?.setActiveConnection?.(newConn.id);
    toast.success(`Connected to ${server.name}`);
    await router.push('/');
    window.location.reload();
  } catch (error: unknown) {
    toast.error(`Failed to add server: ${(error as Error).message}`);
  } finally {
    isConnecting.value = false;
  }
}

async function testManualConnection(): Promise<void> {
  isTestingConnection.value = true;
  testResult.value = null;
  const url = normalizeUrl(manualForm.value.url);
  try {
    const result = await window.electronAPI?.checkVersion?.(url);
    if (result?.compatible) {
      testResult.value = {
        variant: 'success',
        message: `✓ Connection successful! Server version: ${result.serverVersion}`,
      };
    } else {
      testResult.value = {
        variant: 'danger',
        message: result?.error ?? 'Version mismatch',
      };
    }
  } catch (error: unknown) {
    testResult.value = {
      variant: 'danger',
      message: `Connection failed: ${(error as Error).message}`,
    };
  } finally {
    isTestingConnection.value = false;
  }
}

async function addServerOnly(): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;
  try {
    const url = normalizeUrl(manualForm.value.url);
    const versionCheck = await window.electronAPI?.checkVersion?.(url);
    if (!versionCheck?.compatible) {
      const proceed = await confirm(
        `Server version (${versionCheck?.serverVersion ?? 'unknown'}) does not match client version. Add anyway?`,
        { title: 'Version Mismatch', okVariant: 'warning', okTitle: 'Add Anyway' }
      );
      if (!proceed) return;
    }
    await window.electronAPI?.addConnection?.({
      nickname: manualForm.value.nickname,
      url,
      sslEnabled: manualForm.value.sslEnabled,
    });
    toast.success(`Saved ${manualForm.value.nickname}`);
    await loadConnections();
    showAddModal.value = false;
    await checkAllServerStatuses();
  } catch (error: unknown) {
    toast.error(`Failed to add server: ${(error as Error).message}`);
  }
}

async function addAndConnect(): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;
  isConnecting.value = true;
  try {
    const url = normalizeUrl(manualForm.value.url);
    const versionCheck = await window.electronAPI?.checkVersion?.(url);
    if (!versionCheck?.compatible) {
      toast.error(versionCheck?.error ?? 'Server version incompatible');
      return;
    }
    const newConn = await window.electronAPI?.addConnection?.({
      nickname: manualForm.value.nickname,
      url,
      sslEnabled: manualForm.value.sslEnabled,
    });
    if (!newConn) throw new Error('Failed to add connection');
    await window.electronAPI?.setActiveConnection?.(newConn.id);
    toast.success(`Connected to ${manualForm.value.nickname}`);
    await router.push('/');
    window.location.reload();
  } catch (error: unknown) {
    toast.error(`Failed to add connection: ${(error as Error).message}`);
  } finally {
    isConnecting.value = false;
  }
}

function confirmDeleteConnection(connection: ElectronConnection): void {
  connectionToDelete.value = connection;
  showDeleteModal.value = true;
}

async function deleteConnection(): Promise<void> {
  if (!connectionToDelete.value) return;
  try {
    await window.electronAPI?.deleteConnection?.(connectionToDelete.value.id);
    toast.success(`Deleted ${connectionToDelete.value.nickname}`);
    await loadConnections();
  } catch (error: unknown) {
    toast.error(`Failed to delete connection: ${(error as Error).message}`);
  } finally {
    connectionToDelete.value = null;
  }
}

function normalizeUrl(url: string): string {
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    return manualForm.value.sslEnabled ? `https://${url}` : `http://${url}`;
  }
  return url;
}

function formatDate(timestamp: number | null): string {
  if (!timestamp) return 'Never';
  return new Date(timestamp).toLocaleString();
}

function formatTimeAgo(timestamp: number | null): string {
  if (!timestamp) return 'Never';
  const seconds = Math.floor((currentTime.value - timestamp) / 1000);
  if (seconds < 10) return 'Just now';
  if (seconds < 60) return `${seconds} seconds ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)} minutes ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)} hours ago`;
  return `${Math.floor(seconds / 86400)} days ago`;
}

function getStatusVariant(connectionId: string): string {
  const status = serverStatuses.value[connectionId];
  if (!status) return 'secondary';
  if (!status.available) return 'danger';
  if (!status.compatible) return 'warning';
  return 'success';
}

function getStatusText(connectionId: string): string {
  const status = serverStatuses.value[connectionId];
  if (!status) return 'Checking...';
  if (!status.available) return 'Unavailable';
  if (!status.compatible) return 'Version Mismatch';
  return 'Available';
}

function resetManualForm(): void {
  manualForm.value = { nickname: '', url: '', sslEnabled: false };
  testResult.value = null;
  v$.value.$reset();
}

function startAutoDiscovery(): void {
  discoverServers();
  discoveryInterval = setInterval(discoverServers, 15000);
}

function stopAutoDiscovery(): void {
  if (discoveryInterval) {
    clearInterval(discoveryInterval);
    discoveryInterval = null;
  }
}

function startServerStatusPolling(): void {
  checkAllServerStatuses();
  serverStatusPollingInterval = setInterval(checkAllServerStatuses, 30000);
}

function stopServerStatusPolling(): void {
  if (serverStatusPollingInterval) {
    clearInterval(serverStatusPollingInterval);
    serverStatusPollingInterval = null;
  }
}
</script>

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
