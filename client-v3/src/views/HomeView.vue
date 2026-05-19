<template>
  <div class="home">
    <template v-if="settings && (settings as Record<string, unknown>).current_show == null">
      <h1>DigiScript</h1>
      <b>No show has been loaded. Please create a new one, or load an existing one.</b>
    </template>
    <template v-else>
      <h1>{{ currentShow?.name }}</h1>
      <b v-if="currentShowSession == null">
        <template v-if="isAdminUser">
          No live session has currently been started. Please start a live session to continue.
        </template>
        <template v-else>
          No live session has currently been started. Please wait for a live session to start.
        </template>
      </b>
      <b v-else> Live session has been started. Join <RouterLink to="/live">here</RouterLink>. </b>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useSystemStore } from '@/stores/system';
import { useUserStore } from '@/stores/user';
import { useShowStore } from '@/stores/show';

const systemStore = useSystemStore();
const userStore = useUserStore();
const showStore = useShowStore();

const { currentShow, settings } = storeToRefs(systemStore);

const currentShowSession = computed(() => showStore.currentSession);

const isAdminUser = computed(() => userStore.currentUser?.is_admin ?? false);
</script>
