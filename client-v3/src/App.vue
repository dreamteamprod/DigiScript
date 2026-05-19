<template>
  <BApp id="app">
    <BNavbar
      v-if="route.path !== '/electron/server-selector'"
      toggleable="lg"
      variant="info"
      data-bs-theme="dark"
      class="sticky-top"
    >
      <BNavbarBrand to="/"> DigiScript </BNavbarBrand>
      <BNavbarToggle target="nav-collapse" />
      <BCollapse id="nav-collapse" is-nav>
        <BNavbarNav>
          <template v-if="currentShow != null">
            <BNavItem to="/live" :disabled="currentShowSession == null || !websocketHealthy">
              Live
            </BNavItem>
            <BNavItemDropdown
              v-if="systemStore.isShowExecutor || systemStore.isAdminUser"
              text="Live Config"
            >
              <BDropdownItemButton
                :disabled="
                  currentShowSession != null ||
                  !websocketHealthy ||
                  stoppingSession ||
                  startingSession
                "
                @click.stop.prevent="startShowSession"
              >
                Start Session
              </BDropdownItemButton>
              <BDropdownItemButton
                :disabled="
                  currentShowSession == null ||
                  !websocketHealthy ||
                  stoppingSession ||
                  startingSession
                "
                @click.stop.prevent="stopShowSession"
              >
                Stop Session
              </BDropdownItemButton>
              <BDropdownItemButton
                :disabled="
                  currentShowSession == null ||
                  !websocketHealthy ||
                  stoppingSession ||
                  startingSession
                "
                @click.stop.prevent="reloadClients"
              >
                Reload Clients
              </BDropdownItemButton>
              <BDropdownItem
                :disabled="
                  currentShowSession == null ||
                  !websocketHealthy ||
                  stoppingSession ||
                  startingSession
                "
                @click="goToPageModal?.show()"
              >
                Jump To Page
              </BDropdownItem>
            </BNavItemDropdown>
          </template>
          <BNavItem
            v-if="systemStore.isAdminUser"
            v-show="currentShowSession == null"
            to="/config"
            :disabled="!websocketHealthy"
          >
            System Config
          </BNavItem>
          <BNavItem
            v-if="currentShow != null && systemStore.isAllowedShowConfig"
            v-show="currentShowSession == null"
            to="/show-config"
            :disabled="!websocketHealthy"
          >
            Show Config
          </BNavItem>
        </BNavbarNav>
        <BNavbarNav class="ms-auto">
          <BNavItem to="/help"> Help </BNavItem>
          <BNavItem to="/about"> About </BNavItem>
          <BNavItemDropdown v-if="isElectronEnv" text="Server">
            <template #button-content>
              <em>{{ serverConnectionName }}</em>
            </template>
            <BDropdownItemButton @click.stop.prevent="switchServer">
              Switch Server
            </BDropdownItemButton>
          </BNavItemDropdown>
          <BNavItem v-if="userStore.currentUser == null" to="/login"> Login </BNavItem>
          <BNavItemDropdown v-else>
            <template #button-content>
              <em>{{ userStore.currentUser.username }}</em>
            </template>
            <BDropdownItem to="/me"> Settings </BDropdownItem>
            <BDropdownItemButton @click.stop.prevent="userStore.logout()">
              Sign Out
            </BDropdownItemButton>
          </BNavItemDropdown>
          <BNavText id="connection-status" :class="{ healthy: websocketHealthy }">
            <template v-if="websocketHealthy"> Connected </template>
            <template v-else> Disconnected </template>
          </BNavText>
        </BNavbarNav>
      </BCollapse>
    </BNavbar>
    <BNavbar v-else variant="info" data-bs-theme="dark" :sticky="true">
      <BNavbarBrand to="#"> DigiScript </BNavbarBrand>
    </BNavbar>

    <template v-if="!loaded">
      <div class="text-center center-spinner">
        <BSpinner style="width: 10rem; height: 10rem" variant="info" />
      </div>
    </template>
    <template
      v-else-if="settings && (settings as Record<string, unknown>).has_admin_user === false"
    >
      <BContainer class="mx-0" fluid>
        <BRow>
          <BCol>
            <h2>Welcome to DigiScript</h2>
            <b>To get started, please create an admin user!</b>
          </BCol>
        </BRow>
      </BContainer>
    </template>
    <RouterView v-else />

    <ConfirmDialog />

    <BModal
      ref="goToPageModal"
      title="Go to Page"
      size="sm"
      :hide-header-close="changingPage"
      :hide-footer="changingPage"
      :no-close-on-backdrop="changingPage"
      :no-close-on-esc="changingPage"
      @ok="goToLivePage"
    >
      <BForm @submit.stop.prevent="">
        <BFormGroup id="page-input-group" label="Page" label-for="page-input" label-cols="auto">
          <BFormInput
            id="page-input"
            v-model="pageInputState.pageNo"
            name="page-input"
            type="number"
            :state="v$.pageNo.$dirty ? !v$.pageNo.$error : null"
            aria-describedby="page-feedback"
          />
          <BFormInvalidFeedback id="page-feedback">
            This is a required field, and must be greater than 0.
          </BFormInvalidFeedback>
        </BFormGroup>
      </BForm>
    </BModal>
  </BApp>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import type { BModal } from 'bootstrap-vue-next';
import { useVuelidate } from '@vuelidate/core';
import { required, minValue } from '@vuelidate/validators';
import log from 'loglevel';
import { toast } from '@/js/toast';
import { useConfirm } from '@/composables/useConfirm';
import ConfirmDialog from '@/components/common/ConfirmDialog.vue';
import { useUserStore } from '@/stores/user';
import { useSystemStore } from '@/stores/system';
import { useShowStore } from '@/stores/show';
import { useWebSocketStore } from '@/stores/websocket';
import { useWebSocket } from '@/composables/useWebSocket';
import { makeURL } from '@/js/utils';
import { isElectron } from '@/js/platform';

const route = useRoute();
const router = useRouter();
const userStore = useUserStore();
const systemStore = useSystemStore();
const showStore = useShowStore();
const wsStore = useWebSocketStore();

const { websocketHealthy } = storeToRefs(wsStore);
const { currentShow, settings } = storeToRefs(systemStore);

const { sendObj, connect } = useWebSocket();
const { confirm } = useConfirm();

const isElectronEnv = ref(false);

// Local state
const loaded = ref(false);
const stoppingSession = ref(false);
const startingSession = ref(false);
const changingPage = ref(false);
const serverConnectionName = ref('Server');
const goToPageModal = ref<InstanceType<typeof BModal>>();

const currentShowSession = computed(() => showStore.currentSession);

// Jump-to-page form
const pageInputState = ref({ pageNo: 1 });
const pageRules = { pageNo: { required, minValue: minValue(1) } };
const v$ = useVuelidate(pageRules, pageInputState);

let loadTimer: ReturnType<typeof setTimeout> | null = null;

onMounted(async () => {
  isElectronEnv.value = isElectron();

  if (isElectronEnv.value) {
    try {
      const activeConnection = await window.electronAPI?.getActiveConnection?.();
      if (!activeConnection) {
        loaded.value = true;
        return;
      }
      const conn = activeConnection as { nickname?: string; url?: string };
      serverConnectionName.value = conn.nickname ?? conn.url ?? 'Server';
    } catch (error) {
      log.error('Error checking active connection:', error);
      loaded.value = true;
      return;
    }
  }

  if (userStore.authToken) {
    await userStore.refreshToken();
    await userStore.setupTokenRefresh();
  }

  await systemStore.getSettings();
  connect();
  await awaitWSConnect();
});

onBeforeUnmount(() => {
  if (loadTimer) clearTimeout(loadTimer);
});

async function awaitWSConnect(): Promise<void> {
  if (websocketHealthy.value) {
    if (loadTimer) {
      clearTimeout(loadTimer);
      loadTimer = null;
    }
    if (userStore.authToken) {
      await userStore.getCurrentUser();
      await Promise.all([userStore.getCurrentRbac(), userStore.getUserSettings()]);
    }
    if (systemStore.currentShow != null) {
      await showStore.getShowSessionData();
      if (showStore.currentSession != null && route.path !== '/live') {
        await router.push('/live');
      }
    }
    loaded.value = true;
  } else {
    loadTimer = setTimeout(awaitWSConnect, 150);
  }
}

async function stopShowSession(): Promise<void> {
  stoppingSession.value = true;
  const confirmed = await confirm('Are you sure you want to stop the show?', {
    title: 'Stop Show',
    okVariant: 'danger',
    okTitle: 'Stop Show',
  });
  if (confirmed) {
    const response = await fetch(makeURL('/api/v1/show/sessions/stop'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    if (response.ok) {
      toast.success('Stopped show session');
    } else {
      log.error('Unable to stop show session');
      toast.error('Unable to stop show session');
    }
  }
  stoppingSession.value = false;
}

async function startShowSession(): Promise<void> {
  if (!wsStore.internalUUID) {
    toast.error('Unable to start new show session');
    return;
  }
  startingSession.value = true;
  const confirmed = await confirm('Are you sure you want to start a show?', {
    title: 'Start Show',
    okVariant: 'success',
    okTitle: 'Start Show',
  });
  if (confirmed) {
    const response = await fetch(makeURL('/api/v1/show/sessions/start'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: wsStore.internalUUID }),
    });
    if (response.ok) {
      toast.success('Started new show session');
    } else {
      log.error('Unable to start new show session');
      toast.error('Unable to start new show session');
    }
  }
  startingSession.value = false;
}

async function reloadClients(): Promise<void> {
  const confirmed = await confirm('Are you sure you want to reload all connected clients?', {
    title: 'Reload Clients',
    okVariant: 'warning',
    okTitle: 'Reload All',
  });
  if (confirmed) {
    sendObj({ OP: 'RELOAD_CLIENTS', DATA: {} });
  }
}

async function switchServer(): Promise<void> {
  if (!isElectronEnv.value) return;
  const api = window.electronAPI as { clearActiveConnection?: () => Promise<void> } | undefined;
  await api?.clearActiveConnection?.();
  window.location.href = '/ui-new/electron/server-selector';
}

async function goToLivePage(): Promise<void> {
  const valid = await v$.value.$validate();
  if (!valid) return;
  sendObj({ OP: 'LIVE_SHOW_JUMP_TO_PAGE', DATA: { page: pageInputState.value.pageNo } });
  goToPageModal.value?.hide();
}
</script>

<style scoped>
#connection-status {
  color: white;
  font-weight: bold;
  border-radius: 0.25rem;
  padding-left: 0.5rem;
  padding-right: 0.5rem;
  background-color: #e74c3c;
}

#connection-status.healthy {
  background-color: #00bc8c;
}
</style>

<style>
#app {
  text-align: center;
}

div.center-spinner {
  position: fixed;
  top: 50%;
  left: 50%;
  -webkit-transform: translate(-50%, -50%);
  transform: translate(-50%, -50%);
}
</style>
