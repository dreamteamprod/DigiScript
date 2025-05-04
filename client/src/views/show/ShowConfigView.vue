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
              replace
              :to="{'name': 'show-config'}"
              variant="outline-info"
              exact-active-class="active"
            >
              Show
            </b-button>
            <b-button
              replace
              :to="{'name': 'show-config-cast'}"
              variant="outline-info"
              active-class="active"
            >
              Cast
            </b-button>
            <b-button
              replace
              :to="{'name': 'show-config-characters'}"
              variant="outline-info"
              active-class="active"
            >
              Characters
            </b-button>
            <b-button
              replace
              :to="{'name': 'show-config-character-groups'}"
              variant="outline-info"
              active-class="active"
            >
              Character Groups
            </b-button>
            <b-button
              replace
              :to="{'name': 'show-config-acts'}"
              variant="outline-info"
              active-class="active"
            >
              Acts
            </b-button>
            <b-button
              replace
              :to="{'name': 'show-config-scenes'}"
              variant="outline-info"
              active-class="active"
            >
              Scenes
            </b-button>
            <b-button
              replace
              :to="{'name': 'show-config-script'}"
              variant="outline-info"
              active-class="active"
            >
              Script
            </b-button>
            <b-button
              replace
              :to="{'name': 'show-config-cues'}"
              variant="outline-info"
              active-class="active"
            >
              Cues
            </b-button>
            <b-button
              replace
              :to="{'name': 'show-config-mics'}"
              variant="outline-info"
              active-class="active"
            >
              Mics
            </b-button>
            <b-button
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
export default {
  name: 'ShowView',
  data() {
    return {
      navbarHeight: 0,
    };
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
