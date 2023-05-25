<template>
  <div id="app">
    <b-navbar
      toggleable="lg"
      type="dark"
      variant="info"
      :sticky="true"
    >
      <b-navbar-brand to="/">
        DigiScript
      </b-navbar-brand>
      <b-navbar-toggle target="nav-collapse" />
      <b-collapse
        id="nav-collapse"
        is-nav
      >
        <b-navbar-nav>
          <b-nav-item
            to="/live"
            :disabled="CURRENT_SHOW_SESSION == null"
          >
            Live
          </b-nav-item>
          <b-nav-item
            v-if="isAdminUser"
            to="/config"
            :disabled="!WEBSOCKET_HEALTHY || CURRENT_SHOW_SESSION != null"
          >
            System Config
          </b-nav-item>
          <b-nav-item
            v-if="$store.state.currentShow != null && (isAdminUser || isShowEditor)"
            to="/show-config"
            :disabled="!WEBSOCKET_HEALTHY || CURRENT_SHOW_SESSION != null"
          >
            Show Config
          </b-nav-item>
        </b-navbar-nav>
        <b-navbar-nav class="ml-auto">
          <b-nav-item to="/about">
            About
          </b-nav-item>
          <b-nav-item
            v-if="CURRENT_USER == null"
            to="/login"
          >
            Login
          </b-nav-item>
          <b-nav-item-dropdown v-else>
            <template #button-content>
              <em>{{ CURRENT_USER.username }}</em>
            </template>
            <b-dropdown-item-button @click.stop.prevent="USER_LOGOUT">
              Sign Out
            </b-dropdown-item-button>
          </b-nav-item-dropdown>
          <b-nav-text
            id="connection-status"
            :class="{ healthy: WEBSOCKET_HEALTHY }"
            right
          >
            <template v-if="WEBSOCKET_HEALTHY">
              Connected
            </template>
            <template v-else>
              Disconnected
            </template>
          </b-nav-text>
        </b-navbar-nav>
      </b-collapse>
    </b-navbar>
    <template>
      <div
        v-if="!loaded"
        class="text-center center-spinner"
      >
        <b-spinner
          style="width: 10rem; height: 10rem;"
          variant="info"
        />
      </div>
      <template v-else-if="SETTINGS.has_admin_user === false">
        <b-container
          class="mx-0"
          fluid
        >
          <b-row>
            <b-col>
              <h2>Welcome to DigiScript</h2>
              <b>To get started, please create an admin user!</b>
            </b-col>
          </b-row>
          <b-row style="margin-top: 1rem">
            <b-col
              cols="6"
              offset="3"
            >
              <create-user :is_first_admin="true" />
            </b-col>
          </b-row>
        </b-container>
      </template>
      <router-view v-else />
    </template>
  </div>
</template>

<script>
import { getCookie } from '@/js/utils';

import { mapGetters, mapActions } from 'vuex';
import CreateUser from '@/vue_components/user/CreateUser.vue';

export default {
  components: { CreateUser },
  data() {
    return {
      loaded: false,
      loadTimer: null,
    };
  },
  methods: {
    ...mapActions(['GET_SHOW_SESSION_DATA', 'GET_CURRENT_USER', 'USER_LOGOUT', 'GET_RBAC_ROLES',
      'GET_CURRENT_RBAC']),
    async awaitWSConnect() {
      if (this.WEBSOCKET_HEALTHY) {
        clearTimeout(this.loadTimer);
        await this.GET_RBAC_ROLES();
        if (getCookie('digiscript_user_id') != null) {
          await this.GET_CURRENT_USER();
          await this.GET_CURRENT_RBAC();
        }

        if (this.SETTINGS.current_show != null) {
          await this.GET_SHOW_SESSION_DATA();
          this.loaded = true;
          if (this.CURRENT_SHOW_SESSION != null && this.$router.currentRoute.fullPath !== '/live') {
            this.$router.push('/live');
          }
        } else {
          this.loaded = true;
        }
      } else {
        this.loadTimer = setTimeout(this.awaitWSConnect, 150);
      }
    },
  },
  computed: {
    isAdminUser() {
      return this.CURRENT_USER != null && this.CURRENT_USER.is_admin;
    },
    isShowEditor() {
      if (this.RBAC_ROLES.length === 0) {
        return false;
      }
      if (this.CURRENT_USER_RBAC == null || !Object.keys(this.CURRENT_USER_RBAC).includes('shows')) {
        return false;
      }
      const writeMask = this.RBAC_ROLES.find((x) => x.key === 'WRITE').value;
      // eslint-disable-next-line no-bitwise
      return this.CURRENT_USER != null && (this.CURRENT_USER_RBAC.shows[0][1] & writeMask) !== 0;
    },
    ...mapGetters(['WEBSOCKET_HEALTHY', 'CURRENT_SHOW_SESSION', 'SETTINGS', 'CURRENT_USER',
      'RBAC_ROLES', 'CURRENT_USER_RBAC']),
  },
  async created() {
    this.$router.beforeEach(async (to, from, next) => {
      if (!this.SETTINGS.has_admin_user) {
        this.$toast.error('Please create an admin user before continuing');
        next(false);
      } else if (to.fullPath === '/config' && (this.CURRENT_USER == null || !this.CURRENT_USER.is_admin)) {
        next(false);
      } else {
        next();
      }
    });
    await this.awaitWSConnect();
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
