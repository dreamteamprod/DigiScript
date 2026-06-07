<template>
  <div v-if="!loading">
    <BTableSimple>
      <BTbody>
        <BTr>
          <BTd><strong>Version</strong></BTd>
          <BTd>
            {{ versionStatus?.current_version ?? 'Unknown' }}
            <BBadge :variant="versionBadgeVariant" pill>{{ versionBadgeText }}</BBadge>
            <template v-if="versionStatus?.update_available && versionStatus.latest_version">
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
            <template v-if="versionStatus?.check_error">
              <br />
              <small class="text-danger">{{ versionStatus.check_error }}</small>
            </template>
          </BTd>
          <BTd>
            <BButton
              variant="outline-success"
              :disabled="isCheckingVersion"
              @click="checkForUpdates"
            >
              <BSpinner v-if="isCheckingVersion" small class="me-1" />
              Check Now
            </BButton>
          </BTd>
        </BTr>
        <BTr>
          <BTd><strong>Connected Clients</strong></BTd>
          <BTd>{{ connectedSessions.length }}</BTd>
          <BTd>
            <BButton variant="outline-success" @click="clientsModal?.show()">
              View Clients
            </BButton>
          </BTd>
        </BTr>
        <BTr>
          <BTd><strong>Hostname</strong></BTd>
          <BTd>{{ serverInfo?.hostname ?? 'Unknown' }}</BTd>
          <BTd />
        </BTr>
        <BTr>
          <BTd><strong>IP Address</strong></BTd>
          <BTd>{{ serverInfo?.ip_address ?? 'Unknown' }}</BTd>
          <BTd />
        </BTr>
        <BTr>
          <BTd><strong>Port</strong></BTd>
          <BTd>{{ serverInfo?.port ?? 'Unknown' }}</BTd>
          <BTd />
        </BTr>
      </BTbody>
    </BTableSimple>

    <BModal ref="clientsModal" title="Connected Clients" size="lg">
      <BTable
        id="connected-clients-table"
        :items="connectedSessions"
        :fields="clientFields"
        :per-page="perPage"
        :current-page="currentPage"
        small
      />
      <PaginationControls
        v-model:per-page="perPage"
        v-model:current-page="currentPage"
        :total-rows="connectedSessions.length"
        aria-controls="connected-clients-table"
      />
    </BModal>
  </div>
  <div v-else class="text-center">
    <BSpinner style="width: 10rem; height: 10rem" variant="info" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { storeToRefs } from 'pinia';
import { BModal } from 'bootstrap-vue-next';
import { useSystemStore } from '@/stores/system';
import { usePagination } from '@/composables/usePagination';
import { toast } from '@/js/toast';

const systemStore = useSystemStore();
const { connectedSessions, versionStatus, serverInfo } = storeToRefs(systemStore);

const loading = ref(true);
const isCheckingVersion = ref(false);
const { perPage, currentPage } = usePagination();
const clientsModal = ref<InstanceType<typeof BModal>>();

const clientFields = [
  { key: 'internal_id', label: 'UUID' },
  { key: 'remote_ip', label: 'IP' },
  { key: 'is_editor', label: 'Editing Script' },
  'last_ping',
  'last_pong',
];

const versionBadgeVariant = computed(() => {
  if (!versionStatus.value?.current_version) return 'secondary';
  if (versionStatus.value.check_error) return 'danger';
  if (versionStatus.value.update_available) return 'warning';
  return 'success';
});

const versionBadgeText = computed(() => {
  if (!versionStatus.value?.current_version) return 'Loading...';
  if (versionStatus.value.check_error) return 'Unable to check';
  if (versionStatus.value.update_available) return 'Update Available';
  return 'Up to date';
});

async function checkForUpdates(): Promise<void> {
  if (isCheckingVersion.value) return;
  isCheckingVersion.value = true;
  try {
    await systemStore.checkForUpdates();
    if (versionStatus.value?.update_available) {
      toast.info(`Update available: ${versionStatus.value.latest_version}`);
    } else if (!versionStatus.value?.check_error) {
      toast.success('You are running the latest version');
    }
  } catch {
    toast.error('Unable to check for updates');
  } finally {
    isCheckingVersion.value = false;
  }
}

let sessionTimer: ReturnType<typeof setTimeout> | null = null;

function scheduleSessionPoll(): void {
  sessionTimer = setTimeout(async () => {
    await systemStore.getConnectedSessions();
    scheduleSessionPoll();
  }, 1000);
}

onMounted(async () => {
  await Promise.all([
    systemStore.getVersionStatus(),
    systemStore.getConnectedSessions(),
    systemStore.getServerInfo(),
  ]);
  loading.value = false;
  scheduleSessionPoll();
});

onBeforeUnmount(() => {
  if (sessionTimer) clearTimeout(sessionTimer);
});
</script>
