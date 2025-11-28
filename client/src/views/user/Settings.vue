<template>
  <b-container
    fluid
    class="mx-0"
  >
    <h1>User Settings</h1>
    <b-tabs
      pills
      vertical
    >
      <b-tab
        active
        title="About"
      >
        <about-user />
      </b-tab>
      <b-tab title="Settings">
        <user-settings-config />
      </b-tab>
      <b-tab
        title="Stage Direction Styles"
      >
        <stage-direction-styles />
      </b-tab>
      <b-tab title="API Token">
        <api-token />
      </b-tab>
    </b-tabs>
  </b-container>
</template>

<script>
import StageDirectionStyles from '@/vue_components/user/settings/StageDirectionStyles.vue';
import AboutUser from '@/vue_components/user/settings/AboutUser.vue';
import UserSettingsConfig from '@/vue_components/user/settings/Settings.vue';
import ApiToken from '@/vue_components/user/settings/ApiToken.vue';

export default {
  name: 'UserSettings',
  components: {
    UserSettingsConfig, AboutUser, StageDirectionStyles, ApiToken,
  },
};
</script>
