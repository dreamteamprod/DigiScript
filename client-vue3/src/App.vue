<template>
  <div id="app">
    <Menubar :model="menuItems" class="app-header">
      <template #start>
        <div class="navbar-brand">
          <h1>DigiScript v3</h1>
        </div>
      </template>
      <template #end>
        <div class="flex align-items-center gap-2">
          <div v-if="authStore.isAuthenticated" class="user-info flex align-items-center gap-2">
            <i class="pi pi-user"></i>
            <span class="username">{{ authStore.currentUser?.username }}</span>
            <Button
              icon="pi pi-cog"
              size="small"
              outlined
              rounded
              v-tooltip="'User Settings'"
              @click="router.push('/settings')"
            />
            <Button
              icon="pi pi-sign-out"
              size="small"
              outlined
              rounded
              severity="secondary"
              v-tooltip="'Logout'"
              @click="handleLogout"
            />
          </div>
          <div v-else class="auth-buttons flex align-items-center gap-2">
            <Button
              label="Login"
              icon="pi pi-sign-in"
              size="small"
              @click="router.push('/login')"
            />
          </div>
        </div>
      </template>
    </Menubar>

    <main class="main-content">
      <router-view />
    </main>

    <div class="app-footer">
      <p>&copy; 2024 DigiScript - Vue 3 Migration (Phase 3B: Authentication)</p>
    </div>

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
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useConfirm } from 'primevue/useconfirm';
import { useAuthStore } from './stores/auth';

const router = useRouter();
const authStore = useAuthStore();
const confirm = useConfirm();

// Navigation menu items for PrimeVue Menubar
const menuItems = computed(() => {
  const baseItems = [
    {
      label: 'Home',
      icon: 'pi pi-home',
      command: () => {
        router.push('/');
      },
    },
    {
      label: 'About',
      icon: 'pi pi-info-circle',
      command: () => {
        router.push('/about');
      },
    },
    {
      label: 'WebSocket Test',
      icon: 'pi pi-wifi',
      command: () => {
        router.push('/websocket-test');
      },
    },
  ];

  // Add authenticated-only menu items
  if (authStore.isAuthenticated) {
    baseItems.push({
      label: 'Settings',
      icon: 'pi pi-cog',
      command: () => {
        router.push('/settings');
      },
    });
  }

  return baseItems;
});

// Logout handler
function handleLogout() {
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

// Initialize auth on app startup
onMounted(async () => {
  // If we have a token but no current user, try to get current user
  if (authStore.authToken && !authStore.currentUser) {
    try {
      await authStore.getCurrentUser();
      if (authStore.currentUser) {
        await authStore.getUserSettings();
        authStore.setupTokenRefresh();
      }
    } catch (error) {
      console.error('Error initializing auth:', error);
      // Clear invalid token
      authStore.clearAuthData();
    }
  }
});
</script>

<style scoped>
/* Global app styles with PrimeVue integration */
#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  margin-bottom: 0;
  border-radius: 0;
}

.navbar-brand h1 {
  margin: 0;
  font-size: 1.5rem;
  color: var(--p-primary-color);
  font-weight: 600;
}

.main-content {
  flex: 1;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
  width: 100%;
  box-sizing: border-box;
}

.app-footer {
  background: var(--p-surface-100);
  text-align: center;
  padding: 1rem;
  border-top: 1px solid var(--p-surface-200);
  margin-top: auto;
}

.app-footer p {
  margin: 0;
  color: var(--p-text-muted-color);
  font-size: 0.875rem;
}

/* PrimeVue utility classes */
.flex {
  display: flex;
}

.align-items-center {
  align-items: center;
}

.gap-2 {
  gap: 0.5rem;
}

/* User info styling */
.user-info .username {
  font-weight: 500;
  color: var(--p-text-color);
  margin-right: 0.5rem;
}

.auth-buttons {
  margin-left: auto;
}

/* Responsive adjustments */
@media (max-width: 768px) {
  .main-content {
    padding: 1rem;
  }

  .navbar-brand h1 {
    font-size: 1.25rem;
  }

  .user-info .username {
    display: none;
  }
}
</style>
