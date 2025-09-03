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
                <Card>
                  <template #content>
                    <div class="system-overview">
                      <!-- Current Show Status -->
                      <div class="row mb-4">
                        <div class="col-md-3">
                          <strong>Current Show</strong>
                        </div>
                        <div class="col-md-6">
                          <div v-if="settingsStore.currentShowLoaded">
                            <span class="font-semibold">{{ settingsStore.currentShow?.name }}</span>
                            <div class="text-sm text-muted">
                              {{ settingsStore.currentShow?.start_date }} -
                              {{ settingsStore.currentShow?.end_date }}
                            </div>
                          </div>
                          <div v-else>
                            <span class="font-bold text-orange-600">No show loaded</span>
                          </div>
                        </div>
                        <div class="col-md-3">
                          <div class="d-flex gap-2">
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
                      </div>

                      <Divider />

                      <!-- Connected Clients -->
                      <div class="row">
                        <div class="col-md-3">
                          <strong>Connected Clients</strong>
                        </div>
                        <div class="col-md-6">
                          <span class="font-semibold">
                            {{ settingsStore.connectedClients.length }} clients
                          </span>
                          <div
                            v-if="settingsStore.connectedClients.length > 0"
                            class="text-sm text-muted"
                          >
                            Last updated: {{ formatDateTime(new Date().toISOString()) }}
                          </div>
                        </div>
                        <div class="col-md-3">
                          <Button
                            label="View Clients"
                            severity="success"
                            outlined
                            size="small"
                            @click="showClientsModal = true"
                          />
                        </div>
                      </div>
                    </div>
                  </template>
                </Card>
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
import Card from 'primevue/card';
import Button from 'primevue/button';
import Divider from 'primevue/divider';
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
  background-color: #343a40;
  color: white;
  /* Remove min-height: 100vh as this is inside main content which already handles full height */
}

.system-overview {
  /* No padding - content should use full available space */
}

.system-overview .row {
  align-items: center;
}

.text-muted {
  color: #6c757d;
}

.text-orange-600 {
  color: #ea580c;
}

/* Dark theme refinements to match Vue 2 exactly */

/* TabView container styling - force visibility */
:deep(.p-tabview) {
  background-color: #343a40 !important;
  width: 100% !important;
  border: 1px solid #495057 !important;
}

/* Make tabs look like Vue 2 - simple dark background spanning full width */
:deep(.p-tabview-nav) {
  background-color: #495057 !important;
  border-bottom: 1px solid #6c757d !important;
  padding: 0 !important;
  width: 100% !important;
  display: flex !important;
  margin: 0 !important;
  min-height: 50px !important;
}

:deep(.p-tabview-nav-link) {
  background-color: #495057 !important;
  border-right: 1px solid #6c757d !important;
  border-top: 1px solid #6c757d !important;
  border-left: 1px solid #6c757d !important;
  border-bottom: none !important;
  margin-right: 2px !important;
  color: #adb5bd !important;
  padding: 0.75rem 1rem !important;
  cursor: pointer !important;
  border-radius: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  min-height: 50px !important;
  font-weight: bold !important;
  text-decoration: none !important;
}

:deep(.p-tabview-nav-link:first-child) {
  margin-left: 0 !important;
}

:deep(.p-tabview-nav-link:last-child) {
  border-right: 1px solid #6c757d !important;
  margin-right: 0 !important;
}

:deep(.p-tabview-nav-link.p-highlight) {
  background-color: #343a40 !important;
  border-bottom: 1px solid #343a40 !important;
  color: white !important;
  z-index: 1 !important;
  position: relative !important;
}

:deep(.p-tabview-nav-link.p-disabled) {
  color: #6c757d !important;
  cursor: not-allowed !important;
  opacity: 0.6 !important;
}

/* Tab panels - make sure they are visible */
:deep(.p-tabview-panels) {
  background-color: #343a40 !important;
  border: 1px solid #495057 !important;
  border-top: none !important;
  padding: 1rem !important;
  /* Remove fixed min-height to allow natural content flow */
  display: block !important;
}

:deep(.p-tabview-panel) {
  background-color: transparent !important;
  color: white !important;
  padding: 0 !important;
  display: block !important;
}

/* Ensure cards blend with background */
:deep(.p-card) {
  background-color: transparent !important;
  border: 1px solid #495057 !important;
  box-shadow: none !important;
}

/* Success buttons to match Vue 2 green */
:deep(.p-button.p-button-success.p-button-outlined) {
  border-color: #28a745 !important;
  color: #28a745 !important;
  background-color: transparent !important;
}

:deep(.p-button.p-button-success.p-button-outlined:hover) {
  background-color: #28a745 !important;
  color: white !important;
  border-color: #28a745 !important;
}

/* Text styling to match Vue 2 */
h1 {
  color: white !important;
  text-align: center;
  margin-bottom: 2rem;
}

strong {
  color: white !important;
}

.font-semibold {
  color: white !important;
}

.text-sm {
  color: #6c757d !important;
}
</style>
