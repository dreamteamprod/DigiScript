<template>
  <div class="home">
    <template v-if="SETTINGS.current_show == null">
      <h1>DigiScript</h1>
      <b>No show has been loaded. Please create a new one, or load an existing one.</b>
    </template>
    <template v-else>
      <h1>{{ CURRENT_SHOW.name }}</h1>
      <b v-if="CURRENT_SHOW_SESSION == null">
        No live session has currently been started. Please start a live session to continue.
      </b>
      <b v-else>
        Live session has been started. Join <router-link to="/live">here</router-link>.
      </b>
    </template>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  name: 'HomeView',
  computed: {
    ...mapGetters(['SETTINGS', 'CURRENT_SHOW_SESSION', 'CURRENT_SHOW']),
  },
};
</script>
