<template>
  <div id="app">
    <b-navbar toggleable="lg" type="dark" variant="info">
      <b-navbar-brand to="/">
        DigiScript
      </b-navbar-brand>
      <b-navbar-toggle target="nav-collapse"></b-navbar-toggle>
      <b-collapse id="nav-collapse" is-nav>
        <b-navbar-nav>
          <b-nav-item to="/config">System Config</b-nav-item>
          <b-nav-item to="/show-config" v-if="this.$store.state.currentShow != null">
            Show Config
          </b-nav-item>
        </b-navbar-nav>
        <b-navbar-nav class="ml-auto">
          <b-nav-item to="/about">About</b-nav-item>
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
import { mapMutations, mapActions } from 'vuex';

export default {
  data() {
    return {
      loaded: false,
    };
  },
  methods: {
    ...mapActions(['GET_SETTINGS']),
  },
  async created() {
    await this.GET_SETTINGS();
    this.loaded = true;
  },
};
</script>

<style>
#app {
  font-family: Avenir, Helvetica, Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-align: center;
  color: #2c3e50;
}

nav {
  padding: 30px;
}

nav a {
  font-weight: bold;
  color: #2c3e50;
}

nav a.router-link-exact-active {
  color: #42b983;
}

div.center-spinner {
  position: fixed;
  top: 50%;
  left: 50%;
  -webkit-transform: translate(-50%, -50%);
  transform: translate(-50%, -50%);
}
</style>
