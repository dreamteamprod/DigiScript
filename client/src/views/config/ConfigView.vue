<template>
  <b-container
    class="mx-0"
    fluid
  >
    <b-row>
      <b-col>
        <h1>DigiScript Config</h1>
        <b-tabs content-class="mt-3">
          <b-tab
            title="System"
            active
          >
            <config-system />
          </b-tab>
          <b-tab title="Settings">
            <config-settings />
          </b-tab>
          <b-tab
            title="Users"
            :disabled="CURRENT_SHOW == null"
          >
            <config-users />
          </b-tab>
        </b-tabs>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapGetters } from 'vuex';

import ConfigSystem from '@/vue_components/config/ConfigSystem.vue';
import ConfigSettings from '@/vue_components/config/ConfigSettings.vue';
import ConfigUsers from '@/vue_components/config/ConfigUsers.vue';

export default {
  name: 'ConfigView',
  components: { ConfigUsers, ConfigSettings, ConfigSystem },
  computed: {
    ...mapGetters(['CURRENT_SHOW']),
  },
};
</script>
