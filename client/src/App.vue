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
          <template v-if="$store.state.currentShow != null">
            <b-nav-item
              to="/live"
              :disabled="CURRENT_SHOW_SESSION == null || !WEBSOCKET_HEALTHY"
            >
              Live
            </b-nav-item>
            <b-nav-item-dropdown
              v-if="IS_SHOW_EXECUTOR || IS_ADMIN_USER"
              text="Live Config"
            >
              <b-dropdown-item-button
                :disabled="CURRENT_SHOW_SESSION != null || !WEBSOCKET_HEALTHY || stoppingSession ||
                  startingSession"
                @click.stop.prevent="startShowSession"
              >
                Start Session
              </b-dropdown-item-button>
              <b-dropdown-item-button
                :disabled="CURRENT_SHOW_SESSION == null || !WEBSOCKET_HEALTHY || stoppingSession ||
                  startingSession"
                @click.stop.prevent="stopShowSession"
              >
                Stop Session
              </b-dropdown-item-button>
              <b-dropdown-item-btn
                :disabled="CURRENT_SHOW_SESSION == null || !WEBSOCKET_HEALTHY || stoppingSession ||
                  startingSession"
                @click.stop.prevent="reloadClients"
              >
                Reload Clients
              </b-dropdown-item-btn>
              <b-dropdown-item
                v-b-modal.go-to-page
                :disabled="CURRENT_SHOW_SESSION == null || !WEBSOCKET_HEALTHY || stoppingSession || startingSession"
              >
                Jump To Page
              </b-dropdown-item>
            </b-nav-item-dropdown>
          </template>
          <b-nav-item
            v-if="IS_ADMIN_USER"
            v-show="CURRENT_SHOW_SESSION == null"
            to="/config"
            :disabled="!WEBSOCKET_HEALTHY"
          >
            System Config
          </b-nav-item>
          <b-nav-item
            v-if="$store.state.currentShow != null && isAllowedScriptConfig"
            v-show="CURRENT_SHOW_SESSION == null"
            to="/show-config"
            :disabled="!WEBSOCKET_HEALTHY"
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
            <b-dropdown-item to="/me">
              Settings
            </b-dropdown-item>
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
    <template v-if="!loaded">
      <div
        class="text-center center-spinner"
      >
        <b-spinner
          style="width: 10rem; height: 10rem;"
          variant="info"
        />
      </div>
    </template>
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
            <create-user :is-first-admin="true" />
          </b-col>
        </b-row>
      </b-container>
    </template>
    <router-view v-else />
    <b-modal
      id="go-to-page"
      ref="go-to-page"
      title="Go to Page"
      size="sm"
      :hide-header-close="changingPage"
      :hide-footer="changingPage"
      :no-close-on-backdrop="changingPage"
      :no-close-on-esc="changingPage"
      @ok="goToLivePage"
    >
      <b-form @submit.stop.prevent="">
        <b-form-group
          id="page-input-group"
          label="Page"
          label-for="page-input"
          label-cols="auto"
        >
          <b-form-input
            id="page-input"
            v-model="$v.pageInputFormState.pageNo.$model"
            name="page-input"
            type="number"
            :state="validatePageState('pageNo')"
            aria-describedby="page-feedback"
          />
          <b-form-invalid-feedback
            id="page-feedback"
          >
            This is a required field, and must be greater than 0.
          </b-form-invalid-feedback>
        </b-form-group>
      </b-form>
    </b-modal>
  </div>
</template>

<script>
import { mapGetters, mapActions } from 'vuex';
import log from 'loglevel';
import CreateUser from '@/vue_components/user/CreateUser.vue';
import { makeURL } from '@/js/utils';
import { notNull, notNullAndGreaterThanZero } from '@/js/customValidators';
import { required, minValue } from 'vuelidate/lib/validators';

export default {
  components: { CreateUser },
  data() {
    return {
      loaded: false,
      loadTimer: null,
      stoppingSession: false,
      startingSession: false,
      wsStateCheckInterval: null,
      changingPage: false,
      pageInputFormState: {
        pageNo: 1,
      },
    };
  },
  validations: {
    pageInputFormState: {
      pageNo: {
        required,
        notNull,
        notNullAndGreaterThanZero,
        minValue: minValue(1),
      },
    },
  },
  computed: {
    isAllowedScriptConfig() {
      return (this.IS_ADMIN_USER
        || this.IS_SHOW_EDITOR
        || this.IS_SHOW_READER
        || this.IS_SHOW_EXECUTOR
        || this.IS_SCRIPT_READER
        || this.IS_SCRIPT_EDITOR
        || this.IS_CUE_READER
        || this.IS_CUE_EDITOR);
    },
    ...mapGetters([
      'IS_ADMIN_USER',
      'IS_SHOW_EDITOR',
      'WEBSOCKET_HEALTHY',
      'CURRENT_SHOW_SESSION',
      'SETTINGS',
      'CURRENT_USER',
      'RBAC_ROLES',
      'CURRENT_USER_RBAC',
      'INTERNAL_UUID',
      'AUTH_TOKEN',
      'WEBSOCKET_HAS_PENDING_OPERATIONS',
      'IS_SHOW_READER',
      'IS_SHOW_EXECUTOR',
      'IS_SCRIPT_READER',
      'IS_SCRIPT_EDITOR',
      'IS_CUE_READER',
      'IS_CUE_EDITOR',
    ]),
  },
  async created() {
    // If we have a stored auth token, refresh the token to validate we are still logged in,
    // and then set up token refresh
    if (this.AUTH_TOKEN) {
      await this.REFRESH_TOKEN();
      await this.SETUP_TOKEN_REFRESH();
    }

    await this.GET_SETTINGS();
    await this.awaitWSConnect();

    // Set up an interval to check WebSocket state
    this.wsStateCheckInterval = setInterval(() => {
      if (this.WEBSOCKET_HEALTHY && this.WEBSOCKET_HAS_PENDING_OPERATIONS) {
        this.CHECK_WEBSOCKET_STATE();
      }
    }, 500);
  },
  beforeDestroy() {
    // Clean up interval
    if (this.wsStateCheckInterval) {
      clearInterval(this.wsStateCheckInterval);
    }
  },
  methods: {
    ...mapActions([
      'GET_SHOW_SESSION_DATA',
      'GET_CURRENT_USER',
      'USER_LOGOUT',
      'GET_RBAC_ROLES',
      'GET_CURRENT_RBAC',
      'GET_SETTINGS',
      'SETUP_TOKEN_REFRESH',
      'REFRESH_TOKEN',
      'CHECK_WEBSOCKET_STATE',
      'GET_USER_SETTINGS',
    ]),
    async awaitWSConnect() {
      if (this.WEBSOCKET_HEALTHY) {
        clearTimeout(this.loadTimer);
        await this.GET_RBAC_ROLES();

        // Check WebSocket state for any pending operations
        if (this.WEBSOCKET_HAS_PENDING_OPERATIONS) {
          await this.CHECK_WEBSOCKET_STATE();
        }

        // Check for authentication via token first
        if (this.AUTH_TOKEN) {
          // Then get user data
          await this.GET_CURRENT_USER();
          await this.GET_CURRENT_RBAC();
          await this.GET_USER_SETTINGS();
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
    async stopShowSession() {
      this.stoppingSession = true;
      const msg = 'Are you sure you want to stop the show?';
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        const response = await fetch(makeURL('/api/v1/show/sessions/stop'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });

        if (response.ok) {
          this.$toast.success('Stopped show session');
        } else {
          log.error('Unable to stop show session');
          this.$toast.error('Unable to stop show session');
        }
      }
      this.stoppingSession = false;
    },
    async startShowSession() {
      if (this.INTERNAL_UUID == null) {
        this.$toast.error('Unable to start new show session');
        return;
      }
      this.startingSession = true;
      const msg = 'Are you sure you want to start a show?';
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        const response = await fetch(makeURL('/api/v1/show/sessions/start'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: this.INTERNAL_UUID,
          }),
        });

        if (response.ok) {
          this.$toast.success('Started new show session');
        } else {
          log.error('Unable to start new show session');
          this.$toast.error('Unable to start new show session');
        }
      }
      this.startingSession = false;
    },
    async reloadClients() {
      if (this.INTERNAL_UUID == null) {
        this.$toast.error('Unable to start new show session');
        return;
      }
      this.startingSession = true;
      const msg = 'Are you sure you want to reload all connected clients?';
      const action = await this.$bvModal.msgBoxConfirm(msg, {});
      if (action === true) {
        this.$socket.sendObj({
          OP: 'RELOAD_CLIENTS',
          DATA: {},
        });
      }
    },
    validatePageState(name) {
      const { $dirty, $error } = this.$v.pageInputFormState[name];
      return $dirty ? !$error : null;
    },
    async goToLivePage() {
      this.$socket.sendObj({
        OP: 'LIVE_SHOW_JUMP_TO_PAGE',
        DATA: {
          page: this.pageInputFormState.pageNo,
        },
      });
    },
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
