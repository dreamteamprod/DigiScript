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
      <Menubar class="app-header dark-header">
        <template #start>
          <div class="navbar-brand">
            <h1>DigiScript</h1>
          </div>
        </template>
        <template #end>
          <div class="header-nav">
            <span class="nav-link">About</span>
            <span class="nav-link">Login</span>
            <span class="connection-status connected">Connected</span>
          </div>
        </template>
      </Menubar>

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
      <Menubar :model="menuItems" class="app-header dark-header">
        <template #start>
          <div class="navbar-brand">
            <h1>DigiScript</h1>
          </div>
        </template>
        <template #end>
          <div class="header-nav">
            <span class="nav-link" @click="router.push('/about')">About</span>
            <div v-if="authStore.isAuthenticated" class="user-dropdown">
              <Button
                :label="authStore.currentUser?.username || 'User'"
                icon="pi pi-user"
                size="small"
                outlined
                severity="secondary"
                @click="toggleUserMenu"
              />
              <!-- Simple user menu - will be enhanced later -->
              <div v-if="showUserMenu" class="user-menu">
                <div class="menu-item" @click="router.push('/settings')">
                  <i class="pi pi-cog"></i> Settings
                </div>
                <div class="menu-item" @click="handleLogout">
                  <i class="pi pi-sign-out"></i> Sign Out
                </div>
              </div>
            </div>
            <span v-else class="nav-link" @click="router.push('/login')">Login</span>
            <span class="connection-status" :class="{ connected: isConnected }">
              {{ isConnected ? 'Connected' : 'Disconnected' }}
            </span>
          </div>
        </template>
      </Menubar>

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
import Menubar from 'primevue/menubar';
import Button from 'primevue/button';
import Toast from 'primevue/toast';
import ConfirmDialog from 'primevue/confirmdialog';
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useConfirm } from 'primevue/useconfirm';
import { useAuthStore } from './stores/auth';
import { useSettingsStore } from './stores/settings';
import { useWebSocket } from './composables/useWebSocket';
import CreateAdminUser from './components/CreateAdminUser.vue';

const router = useRouter();
const authStore = useAuthStore();
const settingsStore = useSettingsStore();
const confirm = useConfirm();

// WebSocket composable
const { connect, isConnected } = useWebSocket();

// Local state
const loaded = ref(false);
const showUserMenu = ref(false);

// Navigation menu items for PrimeVue Menubar
const menuItems = computed(() => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const baseItems: any[] = [
    {
      label: 'Home',
      icon: 'pi pi-home',
      command: () => {
        router.push('/');
      },
    },
  ];

  // Add Live and Live Config items if there's a current show
  if (settingsStore.currentShow) {
    baseItems.push({
      label: 'Live',
      icon: 'pi pi-play',
      disabled: !settingsStore.currentShow || !isConnected.value,
      command: () => {
        router.push('/live');
      },
    });

    // Live Config dropdown for admins and show executors
    if (authStore.isAuthenticated
      && (authStore.currentUser?.is_admin || authStore.isShowExecutor)) {
      baseItems.push({
        label: 'Live Config',
        icon: 'pi pi-cog',
        items: [
          {
            label: 'Start Session',
            icon: 'pi pi-play',
            disabled: true, // TODO: implement session management
          },
          {
            label: 'Stop Session',
            icon: 'pi pi-stop',
            disabled: true, // TODO: implement session management
          },
          {
            label: 'Reload Clients',
            icon: 'pi pi-refresh',
            disabled: true, // TODO: implement client reload
          },
          {
            label: 'Jump To Page',
            icon: 'pi pi-arrow-right',
            disabled: true, // TODO: implement page jumping
          },
        ],
      });
    }
  }

  // System Config menu for admins
  if (authStore.isAuthenticated && authStore.currentUser?.is_admin) {
    baseItems.push({
      label: 'System Config',
      icon: 'pi pi-wrench',
      disabled: !isConnected.value,
      command: () => {
        router.push('/system-admin');
      },
    });
  }

  // Show Config menu for users with show access
  if (settingsStore.currentShow && authStore.isAuthenticated && authStore.hasShowAccess) {
    baseItems.push({
      label: 'Show Config',
      icon: 'pi pi-database',
      disabled: !isConnected.value,
      command: () => {
        router.push('/show-config');
      },
    });
  }

  // Development/Testing items
  baseItems.push({
    label: 'WebSocket Test',
    icon: 'pi pi-wifi',
    command: () => {
      router.push('/websocket-test');
    },
  });

  return baseItems;
});

// Handlers
function toggleUserMenu() {
  showUserMenu.value = !showUserMenu.value;
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

/* Dark header styling to match Vue 2 */
.app-header.dark-header {
  background-color: #17a2b8 !important;
  border: none !important;
  border-radius: 0;
  padding: 1.875rem;
}

.navbar-brand h1 {
  margin: 0;
  font-size: 1.5rem;
  color: white;
  font-weight: bold;
}

/* Header navigation styling */
.header-nav {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-link {
  color: white;
  font-weight: bold;
  cursor: pointer;
  padding: 0.5rem;
  text-decoration: none;
}

.nav-link:hover {
  color: #00bc8c !important;
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

/* User dropdown */
.user-dropdown {
  position: relative;
}

.user-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
  min-width: 160px;
  z-index: 1000;
  margin-top: 0.25rem;
}

.menu-item {
  padding: 0.5rem 1rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #212529;
  border-bottom: 1px solid #f8f9fa;
}

.menu-item:last-child {
  border-bottom: none;
}

.menu-item:hover {
  background-color: #f8f9fa;
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
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  width: 100%;
  box-sizing: border-box;
  background-color: #343a40;
  color: white;
}

/* Override PrimeVue Menubar dark theme */
:deep(.p-menubar) {
  background-color: #17a2b8 !important;
  border: none !important;
}

:deep(.p-menubar .p-menubar-start) {
  margin-right: auto;
}

:deep(.p-menubar .p-menubar-end) {
  margin-left: auto;
}

:deep(.p-menubar .p-menuitem-link) {
  color: white !important;
}

:deep(.p-menubar .p-menuitem-link:hover) {
  background-color: rgba(255, 255, 255, 0.1) !important;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .main-content {
    padding: 1rem;
  }

  .navbar-brand h1 {
    font-size: 1.25rem;
  }

  .header-nav {
    gap: 1rem;
  }

  .app-header.dark-header {
    padding: 1rem;
  }
}
</style>
