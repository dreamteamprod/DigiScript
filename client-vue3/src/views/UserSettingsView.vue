<template>
  <div class="p-4">
    <h1 class="text-3xl font-bold text-gray-800 mb-6">User Settings</h1>

    <Tabs v-model:value="activeTab">
      <TabList>
        <Tab value="0">About</Tab>
        <Tab value="1">Settings</Tab>
        <Tab value="2">Stage Direction Styles</Tab>
      </TabList>
      <TabPanels>
        <TabPanel value="0">
          <AboutUser />
        </TabPanel>

        <TabPanel value="1">
          <UserSettingsConfig />
        </TabPanel>

        <TabPanel value="2">
          <StageDirectionStyles />
        </TabPanel>
      </TabPanels>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import Tabs from 'primevue/tabs';
import TabList from 'primevue/tablist';
import Tab from 'primevue/tab';
import TabPanels from 'primevue/tabpanels';
import TabPanel from 'primevue/tabpanel';
import AboutUser from '../components/user/AboutUser.vue';
import UserSettingsConfig from '../components/user/UserSettingsConfig.vue';
import StageDirectionStyles from '../components/user/StageDirectionStyles.vue';

// State
const activeTab = ref('0');
</script>

<style scoped>
/* Additional styling can be added here if needed */
</style>
