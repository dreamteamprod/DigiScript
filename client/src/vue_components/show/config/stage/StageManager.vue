<template>
  <b-container
    v-show="loaded"
    class="mx-0 px-0 stage-manager-container"
    fluid
  >
    <div
      class="sticky-header"
      :style="{ top: navbarHeight + 'px' }"
    >
      <b-row class="script-row">
        <b-col cols="2">
          <b-button
            v-b-modal.go-to-scene
            :disabled="orderedScenes.length === 0"
            variant="success"
          >
            Go to Scene
          </b-button>
        </b-col>
        <b-col
          cols="2"
          style="text-align: right"
        >
          <b-button
            variant="success"
            :disabled="currentSceneIndex === 0"
            @click="decrScene"
          >
            Prev Page
          </b-button>
        </b-col>
        <b-col cols="4">
          <p>Current Scene: {{ currentScene }}</p>
        </b-col>
        <b-col
          cols="2"
          style="text-align: left"
        >
          <b-button
            variant="success"
            :disabled="orderedScenes.length === 0 || currentSceneIndex === orderedScenes.length -1"
            @click="incrScene"
          >
            Next Scene
          </b-button>
        </b-col>
        <b-col cols="2">
          <b-dropdown
            :disabled="orderedScenes.length === 0"
            right
            text="Add"
            variant="success"
          >
            <b-dropdown-item-button v-b-modal.add-scenery>
              Scenery
            </b-dropdown-item-button>
            <b-dropdown-item-button v-b-modal.add-prop>
              Prop
            </b-dropdown-item-button>
          </b-dropdown>
        </b-col>
      </b-row>
    </div>
  </b-container>
</template>

<script>
export default {
  name: 'StageManager',
  data() {
    return {
      loaded: false,
      navbarHeight: 0,
      currentSceneIndex: 0,
    };
  },
  computed: {
    orderedScenes() {
      return [];
    },
  },
  mounted() {
    this.loaded = true;
    this.calculateNavbarHeight();
  },
  created() {
    window.addEventListener('resize', this.calculateNavbarHeight);
  },
  destroyed() {
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
.stage-manager-container {
  position: relative;
}

.sticky-header {
  position: sticky;
  z-index: 100;
  padding: 10px 0;
  border-bottom: 1px solid #dee2e6;
  background: var(--body-background);
}
</style>
