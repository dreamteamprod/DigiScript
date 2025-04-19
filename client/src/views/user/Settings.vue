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
    </b-tabs>
  </b-container>
</template>

<script>
import AboutUserUser from '@/vue_components/user/settings/AboutUser.vue';

export default {
  name: 'UserSettings',
  components: { AboutUser: AboutUserUser },
};
</script>
