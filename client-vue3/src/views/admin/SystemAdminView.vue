<template>
  <div class="system-admin">
    <div class="container-fluid mx-0">
      <div class="row">
        <div class="col">
          <h1>DigiScript System Administration</h1>

          <Tabs v-model:value="activeTab">
            <TabList>
              <Tab value="0">System</Tab>
              <Tab value="1">Settings</Tab>
              <Tab value="2" :disabled="!settingsStore.currentShow">Users</Tab>
            </TabList>
            <TabPanels>
              <TabPanel value="0">
                <div class="ds-tab-content">
                  <!-- Current Show Status -->
                  <div class="ds-system-section">
                    <div class="ds-system-section-header">
                      <h3 class="ds-system-section-title">Current Show</h3>
                      <div class="ds-button-group">
                        <Button
                          label="Load Show"
                          severity="success"
                          outlined
                          size="small"
                          :disabled="showsStore.availableShows.length === 0"
                          @click="showLoadModal = true"
                        />
                        <Button
                          label="Setup New Show"
                          severity="success"
                          outlined
                          size="small"
                          @click="showCreateModal = true"
                        />
                      </div>
                    </div>
                    <div class="ds-system-section-content">
                      <div v-if="settingsStore.currentShowLoaded" class="ds-info-grid">
                        <div class="ds-info-grid-label">Show Name:</div>
                        <div class="ds-info-grid-value">
                          <strong>{{ settingsStore.currentShow?.name }}</strong>
                        </div>
                        <div></div>
                      </div>
                      <div v-if="settingsStore.currentShowLoaded" class="ds-info-grid">
                        <div class="ds-info-grid-label">Dates:</div>
                        <div class="ds-info-grid-value ds-muted-text">
                          {{ settingsStore.currentShow?.start_date }} -
                          {{ settingsStore.currentShow?.end_date }}
                        </div>
                        <div></div>
                      </div>
                      <div v-if="!settingsStore.currentShowLoaded" class="ds-info-grid">
                        <div class="ds-info-grid-label">Status:</div>
                        <div class="ds-info-grid-value">
                          <span class="ds-status-indicator warning">No show loaded</span>
                        </div>
                        <div></div>
                      </div>
                    </div>
                  </div>

                  <!-- Connected Clients -->
                  <div class="ds-system-section">
                    <div class="ds-system-section-header">
                      <h3 class="ds-system-section-title">Connected Clients</h3>
                      <Button
                        label="View Clients"
                        severity="success"
                        outlined
                        size="small"
                        @click="showClientsModal = true"
                      />
                    </div>
                    <div class="ds-system-section-content">
                      <div class="ds-info-grid">
                        <div class="ds-info-grid-label">Active Clients:</div>
                        <div class="ds-info-grid-value">
                          <strong>{{ settingsStore.connectedClients.length }} clients</strong>
                        </div>
                        <div></div>
                      </div>
                      <div v-if="settingsStore.connectedClients.length > 0" class="ds-info-grid">
                        <div class="ds-info-grid-label">Last Updated:</div>
                        <div class="ds-info-grid-value ds-muted-text">
                          {{ formatDateTime(new Date().toISOString()) }}
                        </div>
                        <div></div>
                      </div>
                    </div>
                  </div>
                </div>
              </TabPanel>

              <TabPanel value="1">
                <SystemSettingsView />
              </TabPanel>

              <TabPanel value="2">
                <UserManagementView />
              </TabPanel>
            </TabPanels>
          </Tabs>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <CreateShowModal
      v-model="showCreateModal"
      @show-created="onShowCreated"
    />

    <LoadShowModal
      v-model="showLoadModal"
      @show-loaded="onShowLoaded"
    />

    <ConnectedClientsModal
      v-model="showClientsModal"
    />
  </div>
</template>

<script setup lang="ts">
import {
  ref, onMounted, onUnmounted, computed,
} from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from 'primevue/usetoast';
import { useSettingsStore } from '@/stores/settings';
import { useShowsStore } from '@/stores/shows';
import { useAuthStore } from '@/stores/auth';
import type { ShowData } from '@/stores/settings';

// Components
import CreateShowModal from '@/components/admin/CreateShowModal.vue';
import LoadShowModal from '@/components/admin/LoadShowModal.vue';
import ConnectedClientsModal from '@/components/admin/ConnectedClientsModal.vue';

// PrimeVue Components
import Tabs from 'primevue/tabs';
import TabList from 'primevue/tablist';
import Tab from 'primevue/tab';
import TabPanels from 'primevue/tabpanels';
import TabPanel from 'primevue/tabpanel';
import Button from 'primevue/button';
import SystemSettingsView from './SystemSettingsView.vue';
import UserManagementView from './UserManagementView.vue';

const router = useRouter();
const toast = useToast();
const settingsStore = useSettingsStore();
const showsStore = useShowsStore();
const authStore = useAuthStore();

// State
const activeTab = ref('0');
const showCreateModal = ref(false);
const showLoadModal = ref(false);
const showClientsModal = ref(false);
let clientsRefreshInterval: ReturnType<typeof setInterval> | null = null;

// Computed
const isAdmin = computed(() => authStore.currentUser?.is_admin === true);

// Methods
function formatDateTime(dateString: string): string {
  try {
    return new Date(dateString).toLocaleString();
  } catch {
    return dateString;
  }
}

// eslint-disable-next-line no-unused-vars, @typescript-eslint/no-unused-vars
async function onShowCreated(_show: ShowData) {
  // Refresh available shows and update current show if loaded
  await showsStore.getAvailableShows();
  await settingsStore.getSettings(); // Refresh settings to get current show
}

async function onShowLoaded(show: ShowData) {
  // Refresh settings to update current show display
  await settingsStore.getSettings();
  showsStore.setCurrentShow(show);
}

function startClientsRefresh() {
  // Refresh connected clients every 5 seconds
  clientsRefreshInterval = setInterval(async () => {
    try {
      await settingsStore.getConnectedClients();
    } catch (error) {
      console.error('Auto-refresh connected clients error:', error);
    }
  }, 5000);
}

function stopClientsRefresh() {
  if (clientsRefreshInterval) {
    clearInterval(clientsRefreshInterval);
    clientsRefreshInterval = null;
  }
}

// Lifecycle
onMounted(async () => {
  // Check admin permissions
  if (!isAdmin.value) {
    toast.add({
      severity: 'error',
      summary: 'Access Denied',
      detail: 'Admin access required',
      life: 5000,
    });
    router.push('/');
    return;
  }

  try {
    // Load initial data
    await Promise.all([
      showsStore.getAvailableShows(),
      settingsStore.getConnectedClients(),
    ]);

    // Start auto-refresh for connected clients
    startClientsRefresh();
  } catch (error) {
    console.error('Error loading system administration data:', error);
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Unable to load system administration data',
      life: 5000,
    });
  }
});

onUnmounted(() => {
  stopClientsRefresh();
});
</script>

<style scoped>
.system-admin {
  background-color: var(--ds-bg-primary);
  color: var(--ds-text-primary);
}

h1 {
  color: var(--ds-text-primary);
  text-align: center;
  margin-bottom: 2rem;
  font-weight: 600;
}
</style>
