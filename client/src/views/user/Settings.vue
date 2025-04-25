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
      <b-tab
        title="Stage Direction Styles"
      >
        <stage-direction-styles />
      </b-tab>
    </b-tabs>
  </b-container>
</template>

<script>
import StageDirectionStyles from '@/vue_components/user/settings/StageDirectionStyles.vue'
import AboutUserUser from '@/vue_components/user/settings/AboutUser.vue'

export default {
  name: 'UserSettings',
  components: { AboutUser: AboutUserUser, StageDirectionStyles },
}
</script>
