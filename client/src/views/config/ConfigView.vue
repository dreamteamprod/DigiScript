<template>
  <b-container class="mx-0" fluid>
    <b-row>
      <b-col>
        <h1>DigiScript Config</h1>
        <b-tabs content-class="mt-3" lazy>
          <b-tab title="Shows" active>
            <config-shows />
          </b-tab>
          <b-tab title="System">
            <config-system />
          </b-tab>
          <b-tab title="Settings">
            <config-settings />
          </b-tab>
          <b-tab title="Users">
            <config-users />
          </b-tab>
          <b-tab title="Logs">
            <config-logs />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import ConfigSystem from '@/vue_components/config/ConfigSystem.vue';
import ConfigSettings from '@/vue_components/config/ConfigSettings.vue';
import ConfigUsers from '@/vue_components/config/ConfigUsers.vue';
import ConfigShows from '@/vue_components/config/ConfigShows.vue';
import ConfigLogs from '@/vue_components/config/ConfigLogs.vue';

export default {
  name: 'ConfigView',
  components: { ConfigShows, ConfigUsers, ConfigSettings, ConfigSystem, ConfigLogs },
};
</script>
