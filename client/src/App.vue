<template>
  <div id="app">
    <b-navbar toggleable="lg" type="dark" variant="info" :sticky="true">
      <b-navbar-brand to="/">
        DigiScript
      </b-navbar-brand>
      <b-navbar-toggle target="nav-collapse"></b-navbar-toggle>
      <b-collapse id="nav-collapse" is-nav>
        <b-navbar-nav>
          <b-nav-item
            to="/live"
            :disabled="CURRENT_SHOW_SESSION == null">
            Live
          </b-nav-item>
          <b-nav-item
            to="/config"
            :disabled="!WEBSOCKET_HEALTHY || CURRENT_SHOW_SESSION != null">
            System Config
          </b-nav-item>
          <b-nav-item
            to="/show-config"
            v-if="this.$store.state.currentShow != null"
            :disabled="!WEBSOCKET_HEALTHY || CURRENT_SHOW_SESSION != null">
            Show Config
          </b-nav-item>
        </b-navbar-nav>
        <b-navbar-nav class="ml-auto">
          <b-nav-item to="/about">About</b-nav-item>
          <b-nav-text id="connection-status" :class="{ healthy: WEBSOCKET_HEALTHY }">
            <template v-if="WEBSOCKET_HEALTHY">Connected</template>
            <template v-else>Disconnected</template>
          </b-nav-text>
        </b-navbar-nav>
      </b-collapse>
    </b-navbar>
    <template>
      <router-view v-if="loaded"/>
      <div class="text-center center-spinner" v-else>
        <b-spinner style="width: 10rem; height: 10rem;" variant="info"></b-spinner>
      </div>
    </template>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';

export default {
  data() {
    return {
      loaded: false,
    };
  },
  methods: {
    ...mapActions(['GET_SETTINGS', 'GET_SHOW_SESSION_DATA']),
  },
  computed: {
    ...mapGetters(['WEBSOCKET_HEALTHY', 'CURRENT_SHOW_SESSION']),
  },
  async created() {
    await this.GET_SETTINGS();
    await this.GET_SHOW_SESSION_DATA();
    this.loaded = true;
    if (this.CURRENT_SHOW_SESSION != null && this.$router.currentRoute.fullPath !== '/live') {
      this.$router.push('/live');
    }
  },
};
</script>

<style scoped>
#connection-status {
  color: white;
  font-weight: bold;
  border-radius: 0.25rem;
  padding-left: 0.5rem;
  padding-right: 0.5rem;
  background-color: #e74c3c;
}

#connection-status.healthy {
  background-color: #00bc8c;
}
</style>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
}

nav {
  padding: 30px;
}

nav a {
  font-weight: bold;
}

div.center-spinner {
  position: fixed;
  top: 50%;
  left: 50%;
  -webkit-transform: translate(-50%, -50%);
  transform: translate(-50%, -50%);
}
</style>
