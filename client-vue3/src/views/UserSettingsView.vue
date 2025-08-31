<template>
  <div class="p-4">
    <h1 class="text-3xl font-bold text-gray-800 mb-6">User Settings</h1>

    <TabView>
      <TabPanel value="0" header="About">
        <AboutUser />
      </TabPanel>

      <TabPanel value="1" header="Settings">
        <UserSettingsConfig />
      </TabPanel>

      <TabPanel value="2" header="Stage Direction Styles">
        <StageDirectionStyles />
      </TabPanel>
    </TabView>
  </div>
</template>

<script setup lang="ts">
import TabView from 'primevue/tabview';
import TabPanel from 'primevue/tabpanel';
import AboutUser from '../components/user/AboutUser.vue';
import UserSettingsConfig from '../components/user/UserSettingsConfig.vue';
import StageDirectionStyles from '../components/user/StageDirectionStyles.vue';
</script>

<style scoped>
/* Additional styling can be added here if needed */
</style>
