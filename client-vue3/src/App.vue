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
          <i class="pi pi-user"></i>
          <span>Vue 3 + PrimeVue</span>
        </div>
      </template>
    </Menubar>

    <main class="main-content">
      <router-view />
    </main>

    <div class="app-footer">
      <p>&copy; 2024 DigiScript - Vue 3 Migration (Phase 3A)</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import Menubar from 'primevue/menubar';
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

// Navigation menu items for PrimeVue Menubar
const menuItems = ref([
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
]);
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
</style>
