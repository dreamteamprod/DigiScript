<template>
  <div id="app">
    <!-- Loading spinner while initializing -->
    <div v-if="!loaded" class="loading-spinner">
      <div class="spinner">
        <i class="pi pi-spin pi-spinner" style="font-size: 3rem; color: #17a2b8;"></i>
      </div>
    </div>

    <!-- First-time admin setup -->
    <template v-else-if="settingsStore.hasAdminUser === false">
      <nav class="navbar app-header">
        <div class="navbar-brand">
          <h1>DigiScript</h1>
        </div>
        <div class="header-nav">
          <span class="nav-link">About</span>
          <span class="nav-link">Login</span>
          <span class="connection-status connected">Connected</span>
        </div>
      </nav>

      <div class="first-setup-container">
        <div class="setup-content">
          <h2 class="setup-title">Welcome to DigiScript</h2>
          <p class="setup-subtitle">
            <strong>To get started, please create an admin user!</strong>
          </p>
          <div class="setup-form">
            <CreateAdminUser :is-first-admin="true" @user-created="onAdminUserCreated" />
          </div>
        </div>
      </div>
    </template>

    <!-- Normal application layout -->
    <template v-else>
      <Menubar :model="menuItems" class="app-menubar">
        <template #start>
          <div class="brand-section">
            <span class="brand-title" @click="router.push('/')">DigiScript</span>
          </div>
        </template>
        <template #end>
          <div class="end-section">
            <Button
              label="About"
              text
              class="about-button"
              @click="router.push('/about')"
            />
            <Button
              v-if="authStore.isAuthenticated"
              :label="authStore.currentUser?.username || 'User'"
              icon="pi pi-user"
              class="user-button"
              @click="toggleUserMenu"
            />
            <Button
              v-else
              label="Login"
              text
              class="login-button"
              @click="router.push('/login')"
            />
            <Badge
              :value="isConnected ? 'Connected' : 'Disconnected'"
              :severity="isConnected ? 'success' : 'danger'"
              class="connection-badge"
            />
          </div>
        </template>
      </Menubar>

      <!-- User Menu Overlay -->
      <OverlayPanel ref="userMenuPanel">
        <div class="user-menu">
          <div class="user-menu-item" @click="handleUserMenuClick('/settings')">
            <i class="pi pi-cog"></i>
            <span>Settings</span>
          </div>
          <div class="user-menu-item" @click="handleLogout">
            <i class="pi pi-sign-out"></i>
            <span>Sign Out</span>
          </div>
        </div>
      </OverlayPanel>

      <main class="main-content">
        <router-view />
      </main>
    </template>

    <!-- Global PrimeVue components -->
    <Toast />
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import Toast from 'primevue/toast';
import ConfirmDialog from 'primevue/confirmdialog';
import Menubar from 'primevue/menubar';
import Button from 'primevue/button';
import Badge from 'primevue/badge';
import OverlayPanel from 'primevue/overlaypanel';
import {
  onMounted,
  onUnmounted,
  ref,
  computed,
} from 'vue';
import { useRouter } from 'vue-router';
import { useConfirm } from 'primevue/useconfirm';
import { useAuthStore } from './stores/auth';
import { useSettingsStore } from './stores/settings';
import { useWebSocket } from './composables/useWebSocket';
import CreateAdminUser from './components/CreateAdminUser.vue';

// Menu item type for PrimeVue Menubar
interface MenuItem {
  label: string;
  icon?: string;
  disabled?: boolean;
  command?: () => void;
  items?: MenuItem[];
}

const router = useRouter();
const authStore = useAuthStore();
const settingsStore = useSettingsStore();
const confirm = useConfirm();

// WebSocket composable
const { connect, isConnected } = useWebSocket();

// Local state
const loaded = ref(false);
const showUserMenu = ref(false);
const userMenuPanel = ref();

// Computed menu items for PrimeVue Menubar
const menuItems = computed(() => {
  const items: MenuItem[] = [];

  // Live menu item
  if (settingsStore.currentShow) {
    if (authStore.isAuthenticated) {
      const liveItems: MenuItem[] = [
        {
          label: 'Live',
          icon: 'pi pi-play-circle',
          disabled: !settingsStore.currentShow || !isConnected.value,
          command: () => router.push('/live'),
        },
      ];

      // Live Config submenu for admins and show executors
      if (authStore.currentUser?.is_admin || authStore.isShowExecutor) {
        const liveConfigSubitems: MenuItem[] = [
          {
            label: 'Start Session',
            disabled: true,
            command: () => console.log('Start Session - Not implemented'),
          },
          {
            label: 'Stop Session',
            disabled: true,
            command: () => console.log('Stop Session - Not implemented'),
          },
          {
            label: 'Reload Clients',
            disabled: true,
            command: () => console.log('Reload Clients - Not implemented'),
          },
          {
            label: 'Jump To Page',
            disabled: true,
            command: () => console.log('Jump To Page - Not implemented'),
          },
        ];

        liveItems.push({
          label: 'Live Config',
          icon: 'pi pi-cog',
          items: liveConfigSubitems,
        });
      }

      items.push(...liveItems);
    } else {
      items.push({
        label: 'Live',
        icon: 'pi pi-play-circle',
        disabled: true,
      });
    }
  }

  // System Config for admins
  if (authStore.isAuthenticated && authStore.currentUser?.is_admin) {
    items.push({
      label: 'System Config',
      icon: 'pi pi-server',
      disabled: !isConnected.value,
      command: () => router.push('/config'),
    });
  }

  // Show Config for users with show access
  if (settingsStore.currentShow && authStore.isAuthenticated && authStore.hasShowAccess) {
    items.push({
      label: 'Show Config',
      icon: 'pi pi-calendar',
      disabled: !isConnected.value,
      command: () => router.push('/show-config'),
    });
  }

  return items;
});

// Handlers
function toggleUserMenu(event: Event) {
  userMenuPanel.value.toggle(event);
}

function handleUserMenuClick(path: string) {
  userMenuPanel.value.hide();
  router.push(path);
}

function handleLogout() {
  showUserMenu.value = false;
  confirm.require({
    message: 'Are you sure you want to logout?',
    header: 'Confirm Logout',
    icon: 'pi pi-question-circle',
    accept: async () => {
      await authStore.userLogout();
      router.push('/login');
    },
  });
}

async function waitForWebSocket(): Promise<void> {
  return new Promise((resolve) => {
    if (isConnected.value) {
      resolve();
      return;
    }

    const checkConnection = () => {
      if (isConnected.value) {
        resolve();
      } else {
        setTimeout(checkConnection, 150);
      }
    };

    setTimeout(checkConnection, 150);
  });
}

async function onAdminUserCreated() {
  // Refresh settings to update has_admin_user status
  await settingsStore.getSettings();
  loaded.value = true;
}

// Initialize application
async function initializeApp() {
  try {
    // Initialize WebSocket connection first (done automatically by useWebSocket composable)
    connect();

    // Wait for WebSocket to be healthy before proceeding
    await waitForWebSocket();

    // Get system settings to check if admin user exists
    await settingsStore.getSettings();
    await settingsStore.getRbacRoles();

    // If we have a stored auth token, try to authenticate
    if (authStore.authToken) {
      try {
        await authStore.getCurrentUser();
        if (authStore.currentUser) {
          await authStore.getCurrentRbac();
          await authStore.getUserSettings();
          authStore.setupTokenRefresh();
        }
      } catch (error) {
        console.error('Error initializing auth:', error);
        authStore.clearAuthData();
      }
    }

    loaded.value = true;
  } catch (error) {
    console.error('Error initializing app:', error);
    loaded.value = true; // Show app even if there are initialization errors
  }
}

// Initialize app on mount
onMounted(() => {
  initializeApp();
});

// Cleanup on unmount - reserved for future cleanup tasks
onUnmounted(() => {
  // Reserved for cleanup tasks
});
</script>

<style scoped>
/* Global app styles with dark theme matching Vue 2 */
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: #343a40;
  color: #fff;
  text-align: center;
}

/* Loading spinner */
.loading-spinner {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 9999;
}

.spinner {
  text-align: center;
}

/* Navigation bar matching Vue 2 Bootstrap navbar exactly */
.navbar.app-header {
  background-color: #3498DA;
  padding: 15px 30px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: nowrap;
  position: relative;
}

/* Brand styling */
.navbar-brand {
  display: flex;
  align-items: center;
}

.navbar-brand a {
  color: white;
  font-size: 1.5rem;
  font-weight: bold;
  text-decoration: none;
  margin-right: 2rem;
}

.navbar-brand a:hover {
  color: white;
  text-decoration: none;
}

/* Navigation groups */
.navbar-nav-left {
  display: flex;
  align-items: center;
  gap: 0;
  flex: 1;
}

.navbar-nav-right {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

/* Navigation items */
.nav-item {
  position: relative;
}

.nav-link {
  color: white;
  font-weight: bold;
  text-decoration: none;
  padding: 0.5rem 1rem;
  cursor: pointer;
  background: none;
  border: none;
  font-size: 1rem;
  display: inline-block;
  transition: color 0.15s ease-in-out;
}

.nav-link:hover:not(.disabled) {
  color: white;
  text-decoration: none;
}

.nav-link.disabled {
  color: #6c757d;
  cursor: default;
}

/* User link styling to match Vue 2 exactly */
.user-link {
  color: white !important;
  font-weight: bold;
  padding: 0.5rem;
  background: none;
  border: none;
  font-size: 1rem;
  cursor: pointer;
}

.user-link:hover {
  color: white !important;
  text-decoration: none;
}

/* Dropdown styling */
.dropdown {
  position: relative;
  display: inline-block;
}

.dropdown-toggle::after {
  content: "";
  display: inline-block;
  margin-left: 0.255em;
  vertical-align: 0.255em;
  border-top: 0.3em solid;
  border-right: 0.3em solid transparent;
  border-bottom: 0;
  border-left: 0.3em solid transparent;
}

.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1000;
  min-width: 160px;
  padding: 0.5rem 0;
  margin: 0.125rem 0 0;
  background-color: white;
  border: 1px solid rgba(0, 0, 0, 0.15);
  border-radius: 0.25rem;
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.175);
}

.dropdown-menu-right {
  right: 0;
  left: auto;
}

.dropdown-item {
  display: block;
  width: 100%;
  padding: 0.25rem 1rem;
  font-weight: 400;
  color: #212529;
  text-align: inherit;
  text-decoration: none;
  background-color: transparent;
  border: 0;
  cursor: pointer;
}

.dropdown-item:hover:not(.disabled) {
  background-color: #f8f9fa;
  color: #16181b;
  text-decoration: none;
}

.dropdown-item.disabled {
  color: #6c757d;
  pointer-events: none;
  background-color: transparent;
}

/* Connection status styling */
.connection-status {
  color: white;
  font-weight: bold;
  border-radius: 0.25rem;
  padding: 0.25rem 0.5rem;
  background-color: #e74c3c;
  font-size: 0.875rem;
}

.connection-status.connected {
  background-color: #00bc8c;
}

/* First-time setup styling */
.first-setup-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  background-color: #343a40;
}

.setup-content {
  width: 100%;
  max-width: 600px;
}

.setup-title {
  color: white;
  margin-bottom: 1rem;
  font-size: 2rem;
}

.setup-subtitle {
  color: white;
  margin-bottom: 2rem;
  font-size: 1.125rem;
}

.setup-form {
  margin-top: 2rem;
}

/* Main content */
.main-content {
  flex: 1;
  margin: 0;
  padding: 0 15px;
  width: 100%;
  box-sizing: border-box;
  background-color: #343a40;
  color: white;
}

/* PrimeVue Menubar styling overrides */
:deep(.p-menubar) {
  background-color: #3498DA !important;
  border: none !important;
  border-radius: 0 !important;
  padding: 0.75rem 1.5rem !important;
}

:deep(.p-menubar .p-menubar-start) {
  color: white !important;
}

:deep(.p-menubar .p-menubar-end) {
  display: flex !important;
  align-items: center !important;
  gap: 0.75rem !important;
}

/* Brand title styling */
.brand-section .brand-title {
  color: white !important;
  font-size: 1.5rem !important;
  font-weight: bold !important;
  cursor: pointer !important;
  text-decoration: none !important;
}

.brand-section .brand-title:hover {
  color: white !important;
  text-decoration: none !important;
}

/* End section spacing */
.end-section {
  display: flex !important;
  align-items: center !important;
  gap: 0.75rem !important;
}

/* Button styling in navbar */
.end-section .p-button {
  background-color: transparent !important;
  border: none !important;
  color: white !important;
  font-weight: bold !important;
}

.end-section .p-button:hover {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
}

.end-section .user-button {
  background-color: rgba(255, 255, 255, 0.1) !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  border-radius: 0.25rem !important;
}

/* Connection badge styling */
.connection-badge {
  margin-left: 0.25rem !important;
  font-weight: bold !important;
}

/* Menu items in PrimeVue menubar */
:deep(.p-menuitem-link) {
  color: white !important;
  background-color: transparent !important;
  border: none !important;
  padding: 0.5rem 1rem !important;
  border-radius: 0.25rem !important;
}

:deep(.p-menuitem-link:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
  color: white !important;
}

:deep(.p-menuitem-link[data-p-disabled="true"]) {
  color: #6c757d !important;
  cursor: not-allowed !important;
  opacity: 0.6 !important;
}

:deep(.p-menuitem-text) {
  color: white !important;
}

:deep(.p-menuitem-icon) {
  color: white !important;
}

/* User menu styling */
.user-menu {
  min-width: 150px;
  background-color: #343a40 !important;
  border: 1px solid #495057 !important;
  border-radius: 0.25rem !important;
}

.user-menu-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  cursor: pointer;
  color: white;
  transition: background-color 0.15s ease;
}

.user-menu-item:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.user-menu-item i {
  width: 16px;
  text-align: center;
}

/* OverlayPanel dark theme styling */
:deep(.p-overlaypanel) {
  background-color: #343a40 !important;
  border: 1px solid #495057 !important;
  border-radius: 0.25rem !important;
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.4) !important;
}

:deep(.p-overlaypanel .p-overlaypanel-content) {
  background-color: #343a40 !important;
  color: white !important;
  padding: 0 !important;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .main-content {
    padding: 1rem;
  }

  .brand-section .brand-title {
    font-size: 1.25rem !important;
  }

  .end-section {
    gap: 0.5rem !important;
  }

  :deep(.p-menubar) {
    padding: 0.5rem 1rem !important;
  }
}
</style>
