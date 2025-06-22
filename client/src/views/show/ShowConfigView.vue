<template>
  <div class="show">
    <h1>{{ $store.state.currentShow["name"] }}</h1>
    <b-container
      class="mx-0 show-config-container"
      fluid
    >
      <b-row>
        <b-col cols="1">
          <b-button-group
            vertical
            class="sticky-nav"
            :style="{ top: navbarHeight + 'px' }"
          >
            <b-button
              :disabled="!shouldViewShowConfig"
              replace
              :to="{'name': 'show-config'}"
              variant="outline-info"
              exact-active-class="active"
            >
              Show
            </b-button>
            <b-button
              :disabled="!shouldViewShowConfig"
              replace
              :to="{'name': 'show-config-cast'}"
              variant="outline-info"
              active-class="active"
            >
              Cast
            </b-button>
            <b-button
              :disabled="!shouldViewShowConfig"
              replace
              :to="{'name': 'show-config-crew'}"
              variant="outline-info"
              active-class="active"
            >
              Crew
            </b-button>
            <b-button
              :disabled="!shouldViewShowConfig"
              replace
              :to="{'name': 'show-config-characters'}"
              variant="outline-info"
              active-class="active"
            >
              Characters
            </b-button>
            <b-button
              :disabled="!shouldViewShowConfig"
              replace
              :to="{'name': 'show-config-character-groups'}"
              variant="outline-info"
              active-class="active"
            >
              Character Groups
            </b-button>
            <b-button
              :disabled="!shouldViewShowConfig"
              replace
              :to="{'name': 'show-config-acts'}"
              variant="outline-info"
              active-class="active"
            >
              Acts
            </b-button>
            <b-button
              :disabled="!shouldViewShowConfig"
              replace
              :to="{'name': 'show-config-scenes'}"
              variant="outline-info"
              active-class="active"
            >
              Scenes
            </b-button>
            <b-button
              :disabled="!shouldShowScriptConfig"
              replace
              :to="{'name': 'show-config-script'}"
              variant="outline-info"
              active-class="active"
            >
              Script
            </b-button>
            <b-button
              :disabled="!shouldShowCueConfig"
              replace
              :to="{'name': 'show-config-cues'}"
              variant="outline-info"
              active-class="active"
            >
              Cues
            </b-button>
            <b-button
              :disabled="!shouldViewShowConfig"
              replace
              :to="{'name': 'show-config-mics'}"
              variant="outline-info"
              active-class="active"
            >
              Mics
            </b-button>
            <b-button
              :disabled="!shouldShowSessionConfig"
              replace
              :to="{'name': 'show-sessions'}"
              variant="outline-info"
              active-class="active"
            >
              Sessions
            </b-button>
          </b-button-group>
        </b-col>
        <b-col cols="11">
          <router-view />
        </b-col>
      </b-row>
    </b-container>
  </div>
</template>

<script>
import { mapGetters } from 'vuex';

export default {
  name: 'ShowView',
  data() {
    return {
      navbarHeight: 0,
    };
  },
  computed: {
    ...mapGetters(['IS_SHOW_EDITOR', 'IS_SHOW_READER', 'IS_CUE_EDITOR', 'IS_CUE_READER', 'IS_SCRIPT_EDITOR', 'IS_SCRIPT_READER', 'IS_SHOW_EXECUTOR']),
    shouldViewShowConfig() {
      return this.IS_SHOW_EDITOR || this.IS_SHOW_READER;
    },
    shouldShowCueConfig() {
      return this.shouldViewShowConfig || this.IS_CUE_EDITOR || this.IS_CUE_READER;
    },
    shouldShowScriptConfig() {
      return this.shouldViewShowConfig || this.IS_SCRIPT_EDITOR || this.IS_SCRIPT_READER;
    },
    shouldShowSessionConfig() {
      return this.shouldViewShowConfig || this.IS_SHOW_EXECUTOR;
    },
    requiresRedirect() {
      return !this.shouldViewShowConfig && !this.shouldShowCueConfig && !this.shouldShowScriptConfig && !this.shouldShowSessionConfig;
    },
  },
  watch: {
    requiresRedirect() {
      if (this.requiresRedirect) {
        this.$toast.warning('Something went wrong viewing show config page');
        this.$router.replace('/');
      }
    },
  },
  beforeMount() {
    if (!this.shouldViewShowConfig) {
      if (this.shouldShowCueConfig) {
        this.$router.replace({ name: 'show-config-cues' });
      } else if (this.shouldShowScriptConfig) {
        this.$router.replace({ name: 'show-config-script' });
      } else if (this.shouldShowSessionConfig) {
        this.$router.replace({ name: 'show-sessions' });
      } else {
        this.$toast.warning('Something went wrong viewing show config page');
        this.$router.replace('/');
      }
    }
  },
  mounted() {
    this.calculateNavbarHeight();
    window.addEventListener('resize', this.calculateNavbarHeight);
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.calculateNavbarHeight);
  },
  methods: {
    calculateNavbarHeight() {
      const navbar = document.querySelector('.navbar');
      if (navbar) {
        this.navbarHeight = navbar.offsetHeight;
      } else {
        this.navbarHeight = 56;
      }
    },
  },
};
</script>

<style scoped>
.show-config-container {
  position: relative;
}

.sticky-nav {
  position: sticky;
  padding: 10px 0;
  background: var(--body-background);
}
</style>
