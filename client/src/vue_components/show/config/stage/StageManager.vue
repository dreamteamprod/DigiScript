<template>
  <b-container class="mx-0 px-0 stage-manager-container" fluid>
    <template v-if="loaded && orderedScenes.length > 0">
      <div class="sticky-header" :style="{ top: navbarHeight + 'px' }">
        <b-row>
          <b-col cols="2">
            <b-button
              v-b-modal.go-to-scene
              :disabled="orderedScenes.length === 0"
              variant="success"
            >
              Go to Scene
            </b-button>
          </b-col>
          <b-col cols="2" style="text-align: right">
            <b-button variant="success" :disabled="currentSceneIndex === 0" @click="decrScene">
              Prev Scene
            </b-button>
          </b-col>
          <b-col cols="4">
            <b>{{ currentSceneLabel }}</b>
          </b-col>
          <b-col cols="2" style="text-align: left">
            <b-button
              variant="success"
              :disabled="
                orderedScenes.length === 0 || currentSceneIndex === orderedScenes.length - 1
              "
              @click="incrScene"
            >
              Next Scene
            </b-button>
          </b-col>
          <b-col cols="2">
            <b-dropdown :disabled="orderedScenes.length === 0" right text="Add" variant="success">
              <b-dropdown-item-button v-b-modal.add-scenery> Scenery </b-dropdown-item-button>
              <b-dropdown-item-button v-b-modal.add-prop> Prop </b-dropdown-item-button>
            </b-dropdown>
          </b-col>
        </b-row>
      </div>
      <b-row style="margin-top: 0.5rem">
        <b-col cols="6">
          <h5>Scenery</h5>
        </b-col>
        <b-col cols="6">
          <h5>Props</h5>
        </b-col>
      </b-row>
    </template>
    <b-row v-else>
      <b-col>
        <b-alert v-if="loaded" variant="danger" show>
          There are no scenes configured for this show.
        </b-alert>
        <div v-else class="text-center py-5">
          <b-spinner label="Loading" />
        </div>
      </b-col>
    </b-row>
  </b-container>
</template>

<script>
import { mapActions, mapGetters } from 'vuex';

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
      return this.ORDERED_SCENES;
    },
    currentScene() {
      if (
        this.currentSceneIndex >= 0 &&
        this.orderedScenes.length > 0 &&
        this.currentSceneIndex < this.orderedScenes.length
      ) {
        return this.orderedScenes[this.currentSceneIndex];
      }
      return null;
    },
    currentSceneLabel() {
      if (this.currentScene != null) {
        return `${this.ACT_BY_ID(this.currentScene.act).name}: ${this.currentScene.name}`;
      }
      return 'N/A';
    },
    ...mapGetters(['ORDERED_SCENES', 'ACT_BY_ID']),
  },
  async mounted() {
    await this.GET_ACT_LIST();
    await this.GET_SCENE_LIST();
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
    incrScene() {
      if (this.currentSceneIndex < this.orderedScenes.length - 1) {
        this.currentSceneIndex += 1;
      }
    },
    decrScene() {
      if (this.currentSceneIndex > 0) {
        this.currentSceneIndex -= 1;
      }
    },
    ...mapActions(['GET_ACT_LIST', 'GET_SCENE_LIST']),
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
