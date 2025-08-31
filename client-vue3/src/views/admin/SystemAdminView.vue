<template>
  <div class="system-admin">
    <div class="container-fluid mx-0">
      <div class="row">
        <div class="col">
          <h1>DigiScript System Administration</h1>

          <TabView>
            <TabPanel value="0" header="System">
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
                            {{ settingsStore.currentShow?.start_date }} - {{ settingsStore.currentShow?.end_date }}
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
                        <span class="font-semibold">{{ settingsStore.connectedClients.length }} clients</span>
                        <div v-if="settingsStore.connectedClients.length > 0" class="text-sm text-muted">
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

            <TabPanel value="1" header="Settings">
              <SystemSettingsView />
            </TabPanel>

            <TabPanel
              value="2"
              header="Users"
              :disabled="!settingsStore.currentShow"
            >
              <Card>
                <template #content>
                  <div class="text-center py-4">
                    <p class="text-muted">User management functionality will be implemented in Phase 4.</p>
                  </div>
                </template>
              </Card>
            </TabPanel>
          </TabView>
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
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import Card from 'primevue/card';
import Button from 'primevue/button';
import Divider from 'primevue/divider';
import SystemSettingsView from './SystemSettingsView.vue';

const router = useRouter();
const toast = useToast();
const settingsStore = useSettingsStore();
const showsStore = useShowsStore();
const authStore = useAuthStore();

// State
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
  padding: 2rem;
}

.system-overview {
  padding: 1rem 0;
}

.system-overview .row {
  align-items: center;
}

.text-muted {
  color: var(--text-color-secondary);
}

.text-orange-600 {
  color: #ea580c;
}
</style>
