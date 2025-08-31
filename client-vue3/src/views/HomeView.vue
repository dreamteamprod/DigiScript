<template>
  <div class="home">
    <!-- No show loaded state -->
    <template v-if="!settingsStore.settings.current_show">
      <h1>DigiScript</h1>
      <p class="no-show-message">
        <strong>No show has been loaded. Please create a new one, or load an existing one.</strong>
      </p>
    </template>

    <!-- Show loaded state -->
    <template v-else>
      <h1>{{ settingsStore.currentShow?.name || 'Current Show' }}</h1>

      <!-- No session state -->
      <template v-if="!currentShowSession">
        <p v-if="authStore.isAdmin" class="session-message">
          <strong>
            No live session has currently been started. Please start a live session to continue.
          </strong>
        </p>
        <p v-else class="session-message">
          <strong>
            No live session has currently been started. Please wait for a live session to start.
          </strong>
        </p>
      </template>

      <!-- Session active state -->
      <template v-else>
        <p class="session-message">
          <strong>
            Live session has been started. Join
            <router-link to="/live" class="live-link">here</router-link>.
          </strong>
        </p>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useSettingsStore } from '../stores/settings';

// Stores
const authStore = useAuthStore();
const settingsStore = useSettingsStore();

// TODO: Add show session management when that store is created
const currentShowSession = computed(() => null);
</script>

<style scoped>
.home {
  padding: 2rem 0;
  color: white;
}

.home h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
  color: white;
}

.no-show-message,
.session-message {
  font-size: 1.125rem;
  color: white;
  margin-bottom: 0;
  line-height: 1.6;
}

.live-link {
  color: #00bc8c;
  text-decoration: none;
}

.live-link:hover {
  color: #00d9a5;
  text-decoration: underline;
}
</style>
